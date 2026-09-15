"""
Script one-shot (mas seguro de rodar mais de uma vez): le a planilha exportada
do formulario "Experiencia Profissional Docentes e Servidores da UPE", limpa
os dados e carrega na collection MongoDB `docentes`.

Cada docente fica identificado pelo e-mail (normalizado/unico) e guarda suas
`areas_interesse` e `segmentos` de interesse, usados futuramente para
notificar por e-mail sobre novos editais compativeis (task 2 e 3).

As AREAS DE INTERESSE da planilha usam o mesmo catalogo fixo de 8 valores que
o Gemini usa para classificar editais (`pipeline.pdf_pipeline.analyzer.AREAS_INTERESSE`),
entao reaproveitamos essa lista aqui para garantir que os textos fiquem
identicos aos gravados em `editais.resultado.areas_interesse`.

Valores de area fora desse catalogo NAO sao gravados em `areas_interesse` (um
docente com uma "area" que o algoritmo de matching nunca vai reconhecer e um
docente que nunca vai ser notificado de nada, silenciosamente - ver
pipeline/orchestration/docente_match.py). Eles ficam separados em
`areas_rejeitadas`, reportados no resumo, para revisao manual.

Uso (dentro da pasta sandbox/, com o venv ativado):
    python import_docentes_interesse.py                 # dry-run: so mostra o resumo
    python import_docentes_interesse.py --apply          # grava de verdade no MongoDB
    python import_docentes_interesse.py --input caminho.xlsx --apply
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import certifi
import openpyxl
from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError

# garante que a raiz do projeto esteja no PYTHONPATH (para importar "pipeline")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.pdf_pipeline.analyzer import AREAS_INTERESSE  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_INPUT_PATH = (
    PROJECT_ROOT
    / "TRATADO - Experiência Profissional Docentes e Servidores da UPE (respostas).xlsx"
)
DOCENTES_COLLECTION = "docentes"
ORIGEM = "planilha_docentes_2026"

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_email(raw: str | None) -> str:
    """Remove espacos (inclusive internos, tipo 'luis. barros@upe.br') e baixa a caixa."""
    return re.sub(r"\s+", "", (raw or "")).strip().lower()


def split_areas(raw: str | None, catalog: list[str]) -> tuple[list[str], list[str]]:
    """
    Separa a celula de AREAS DE INTERESSE nos valores atomicos do catalogo fixo.

    Nao da pra usar split(",") direto: alguns valores atomicos ja tem virgula
    dentro (ex.: "Empreendedorismo (apoio a startups, spin-offs)"). Em vez
    disso, casamos por prefixo contra o catalogo conhecido (do maior pro
    menor, pra evitar ambiguidade) e consumimos a string aos poucos.

    Devolve (conhecidas, rejeitadas): valores que nao casam com nenhum prefixo
    do catalogo vao para "rejeitadas" em vez de virar uma "area" livre -
    gravar isso no Mongo criaria um docente que nunca bate com o catalogo do
    Gemini e, portanto, nunca e notificado de nada (ver docente_match.py).
    """
    text = (raw or "").strip()
    if not text:
        return [], []

    sorted_catalog = sorted(catalog, key=len, reverse=True)
    known: list[str] = []
    rejected: list[str] = []
    remaining = text
    while remaining:
        remaining = remaining.strip().lstrip(",").strip()
        if not remaining:
            break
        matched = next((c for c in sorted_catalog if remaining.startswith(c)), None)
        if matched is None:
            # sobra fora do catalogo conhecido: guarda para revisao manual, sem
            # gravar como area valida
            rejected.append(remaining)
            break
        known.append(matched)
        remaining = remaining[len(matched):]

    def dedup(items: list[str]) -> list[str]:
        seen: set[str] = set()
        return [item for item in items if not (item in seen or seen.add(item))]

    return dedup(known), dedup(rejected)


def split_segmentos(raw: str | None) -> list[str]:
    """Separa a celula de SEGMENTOS por virgula (valores atomicos nao tem virgula interna)."""
    text = (raw or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in text.split(",")]
    seen: set[str] = set()
    return [p for p in parts if p and not (p in seen or seen.add(p))]


def read_rows(path: Path):
    """Le (email, areas_raw, segmentos_raw) de cada linha de dados da planilha."""
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    rows = sheet.iter_rows(values_only=True)
    next(rows, None)  # cabecalho
    for row in rows:
        email = row[0] if len(row) > 0 else None
        areas = row[1] if len(row) > 1 else None
        segmentos = row[2] if len(row) > 2 else None
        yield (str(email) if email is not None else ""), \
              (str(areas) if areas is not None else ""), \
              (str(segmentos) if segmentos is not None else "")


def build_docentes(path: Path, catalog_areas: list[str]):
    """
    Le a planilha inteira e devolve (by_email, stats, report):

    - by_email: dict email -> {"email", "areas_interesse", "segmentos"} pronto
      para gravar no Mongo (so contem valores validos do catalogo).
    - stats: contadores gerais (linhas totais, descartadas, duplicadas, etc.).
    - report: detalhe para revisao humana, nao gravado no Mongo:
        - "areas_rejeitadas": dict email -> lista de textos fora do catalogo
        - "duplicatas_divergentes": lista de emails cuja segunda ocorrencia
          trouxe areas/segmentos diferentes da primeira (o merge continua
          acontecendo do jeito atual, so passa a ser reportado)
    """
    stats = defaultdict(int)
    by_email: dict[str, dict] = {}
    areas_rejeitadas: dict[str, list[str]] = {}
    duplicatas_divergentes: list[str] = []

    for email_raw, areas_raw, segmentos_raw in read_rows(path):
        stats["total_rows"] += 1

        email = normalize_email(email_raw)
        if not email:
            stats["sem_email"] += 1
            continue
        if not EMAIL_REGEX.match(email):
            stats["email_invalido"] += 1
            logger.warning("e-mail invalido ignorado: %r", email_raw)
            continue

        areas, rejeitadas = split_areas(areas_raw, catalog_areas)
        if rejeitadas:
            areas_rejeitadas.setdefault(email, [])
            for item in rejeitadas:
                if item not in areas_rejeitadas[email]:
                    areas_rejeitadas[email].append(item)
        segmentos = split_segmentos(segmentos_raw)

        existing = by_email.get(email)
        if existing is not None:
            stats["linhas_duplicadas"] += 1
            if set(existing["areas_interesse"]) != set(areas) or set(existing["segmentos"]) != set(segmentos):
                duplicatas_divergentes.append(email)
            # une valores caso as duplicatas divirjam (nao esperado, mas seguro)
            existing["areas_interesse"] = sorted(set(existing["areas_interesse"]) | set(areas))
            existing["segmentos"] = sorted(set(existing["segmentos"]) | set(segmentos))
            continue

        by_email[email] = {"email": email, "areas_interesse": areas, "segmentos": segmentos}
        stats["docentes_unicos"] += 1

    report = {
        "areas_rejeitadas": areas_rejeitadas,
        "duplicatas_divergentes": duplicatas_divergentes,
    }
    return by_email, stats, report


def get_mongo_collection():
    uri = (os.getenv("MONGODB_URI") or "").strip()
    if not uri:
        raise RuntimeError("MONGODB_URI nao definido no .env")
    db_name = (os.getenv("MONGODB_DB") or "iaupe-analyser").strip()

    client = MongoClient(uri, tlsCAFile=certifi.where())
    collection = client[db_name][DOCENTES_COLLECTION]
    collection.create_index([("email", ASCENDING)], unique=True)
    return collection


def print_summary(by_email: dict, stats: dict, report: dict) -> None:
    areas_rejeitadas = report["areas_rejeitadas"]
    duplicatas_divergentes = report["duplicatas_divergentes"]

    logger.info("=== Resumo da limpeza ===")
    logger.info("Linhas na planilha (sem cabecalho): %s", stats["total_rows"])
    logger.info("  sem e-mail (descartadas): %s", stats["sem_email"])
    logger.info("  e-mail invalido (descartadas): %s", stats["email_invalido"])
    logger.info("  linhas duplicadas (mesmo e-mail): %s", stats["linhas_duplicadas"])
    logger.info("Docentes unicos a importar: %s", len(by_email))

    if areas_rejeitadas:
        logger.warning(
            "valores de AREAS DE INTERESSE fora do catalogo (%s docente(s) afetado(s), nao gravados):",
            len(areas_rejeitadas),
        )
        for email, valores in sorted(areas_rejeitadas.items()):
            logger.warning("  - %s: %s", email, valores)

    if duplicatas_divergentes:
        logger.warning(
            "e-mails duplicados na planilha com areas/segmentos divergentes entre as linhas (%s):",
            len(duplicatas_divergentes),
        )
        for email in duplicatas_divergentes:
            logger.warning("  - %s", email)

    sem_area = sum(1 for d in by_email.values() if not d["areas_interesse"])
    sem_segmento = sum(1 for d in by_email.values() if not d["segmentos"])
    logger.info("Docentes sem nenhuma area de interesse valida: %s", sem_area)
    logger.info("Docentes sem nenhum segmento marcado: %s", sem_segmento)

    logger.info("=== Amostra (5 primeiros) ===")
    for doc in list(by_email.values())[:5]:
        logger.info(" - %s", doc["email"])
        logger.info("     areas: %s", doc["areas_interesse"])
        logger.info("     segmentos: %s", doc["segmentos"])


def main() -> None:
    # console do Windows costuma usar codepage legado; forca UTF-8 pra nao
    # embaralhar acentos na saida (nao afeta o que e gravado no MongoDB)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # usa o stdout (ja em utf-8 acima) em vez do stderr padrao do logging, ou
    # os acentos saem corrompidos no console legado do Windows
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stdout)

    parser = argparse.ArgumentParser(
        description='Limpa a planilha de docentes e carrega na collection MongoDB "docentes".'
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT_PATH), help="Caminho do arquivo .xlsx")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Executa de fato a gravacao no MongoDB (sem essa flag, roda em modo dry-run)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Arquivo nao encontrado: %s", input_path)
        return

    by_email, stats, report = build_docentes(input_path, AREAS_INTERESSE)
    print_summary(by_email, stats, report)

    if not args.apply:
        logger.info("[dry-run] Nenhuma gravacao feita no MongoDB. Rode novamente com --apply para gravar de verdade.")
        return

    load_dotenv(override=True)
    try:
        collection = get_mongo_collection()
    except (RuntimeError, PyMongoError) as exc:
        logger.error("[MongoDB] Nao foi possivel conectar: %s", exc)
        return

    now = datetime.now(timezone.utc)
    inserted = 0
    updated = 0
    for doc in by_email.values():
        result = collection.update_one(
            {"email": doc["email"]},
            {
                "$set": {
                    "areas_interesse": doc["areas_interesse"],
                    "segmentos": doc["segmentos"],
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "email": doc["email"],
                    "origem": ORIGEM,
                    "created_at": now,
                },
            },
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1
        else:
            updated += 1

    logger.info("Gravacao concluida: %s inseridos, %s atualizados.", inserted, updated)
    logger.info("Total agora em '%s': %s", DOCENTES_COLLECTION, collection.count_documents({}))


if __name__ == "__main__":
    main()
