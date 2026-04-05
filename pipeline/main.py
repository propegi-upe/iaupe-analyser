import argparse
import json
import os
import re
import time
from datetime import datetime, timezone

from sources import scraper_capes, scraper_cnpq, scraper_facepe, scraper_finep
from pdf_pipeline.extractor import extract_text_from_pdf_url
from pdf_pipeline.analyzer import analyze_text
from db.mongo import already_exists, save

SOURCE_REGISTRY = {
    scraper_facepe.SOURCE_KEY: {
        "label": scraper_facepe.SOURCE_LABEL,
        "base_url": scraper_facepe.BASE_URL,
        "mongo_collection": scraper_facepe.MONGO_COLLECTION,
        "collect_links": scraper_facepe.collect_links,
    },
    scraper_cnpq.SOURCE_KEY: {
        "label": scraper_cnpq.SOURCE_LABEL,
        "base_url": scraper_cnpq.BASE_URL,
        "mongo_collection": scraper_cnpq.MONGO_COLLECTION,
        "collect_links": scraper_cnpq.collect_links,
    },
    scraper_finep.SOURCE_KEY: {
        "label": scraper_finep.SOURCE_LABEL,
        "base_url": scraper_finep.BASE_URL,
        "mongo_collection": scraper_finep.MONGO_COLLECTION,
        "collect_links": scraper_finep.collect_links,
    },
    scraper_capes.SOURCE_KEY: {
        "label": scraper_capes.SOURCE_LABEL,
        "base_url": scraper_capes.BASE_URL,
        "mongo_collection": scraper_capes.MONGO_COLLECTION,
        "collect_links": scraper_capes.collect_links,
    },
}

DEFAULT_SOURCE = (os.getenv("PIPELINE_SOURCE") or "facepe").strip().lower()


def parse_limit(raw_value: str | None) -> int | None:
    raw_limit = (raw_value or "all").strip().lower()
    return None if raw_limit in ("all", "0", "none", "") else int(raw_limit)


def get_source_config(source_key: str | None) -> tuple[str, dict]:
    selected_key = (source_key or DEFAULT_SOURCE).strip().lower()
    source = SOURCE_REGISTRY.get(selected_key)
    if source is None:
        disponiveis = ", ".join(sorted(SOURCE_REGISTRY))
        raise ValueError(f"Fonte invalida: {selected_key!r}. Opcoes: {disponiveis}")
    return selected_key, source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pipeline de analise de editais com fontes plugaveis"
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help=f"Fonte alvo ({', '.join(sorted(SOURCE_REGISTRY))})",
    )
    parser.add_argument(
        "--limit",
        default=os.getenv("PIPELINE_LIMIT") or "all",
        help="Limite de PDFs (all, 0, none ou numero inteiro)",
    )
    return parser

LIMIT = parse_limit(os.getenv("PIPELINE_LIMIT"))

SLEEP_ALREADY_EXISTS = int((os.getenv("SLEEP_ALREADY_EXISTS") or "5").strip())
SLEEP_NEW_PROCESS = int((os.getenv("SLEEP_NEW_PROCESS") or "60").strip())
SLEEP_EMPTY_TEXT = int((os.getenv("SLEEP_EMPTY_TEXT") or "5").strip())

MAX_RETRIES_GEMINI = int((os.getenv("MAX_RETRIES_GEMINI") or "3").strip())


def sleep_retry_429(raw: str) -> bool:
    """
    Se a mensagem do Gemini indicar 'Please retry in XXs', aguarda esse tempo e retorna True.
    Caso não consiga extrair o tempo, retorna False.
    """
    m = re.search(r"retry in ([0-9]+(\.[0-9]+)?)s", (raw or "").lower())
    if not m:
        return False

    secs = int(float(m.group(1))) + 2
    print(f"⏳ Gemini 429: aguardando {secs}s e tentando novamente...")
    time.sleep(secs)
    return True


def retry_analyze_text(texto: str, link: str) -> dict:
    """
    Tenta analisar o texto com retry para erros temporários do Gemini:
    - 429: respeita o tempo sugerido
    - 503: aguarda progressivamente e tenta novamente
    """
    for tentativa in range(1, MAX_RETRIES_GEMINI + 1):
        resultado = analyze_text(texto, link)

        if not resultado.get("erro"):
            return resultado

        raw = (resultado.get("raw") or "").lower()

        if "429" in raw:
            if tentativa < MAX_RETRIES_GEMINI and sleep_retry_429(raw):
                continue
            return resultado

        if "503" in raw:
            if tentativa < MAX_RETRIES_GEMINI:
                espera = 30 * tentativa
                print(
                    f"⏳ Gemini 503: aguardando {espera}s antes da tentativa {tentativa + 1}/{MAX_RETRIES_GEMINI}..."
                )
                time.sleep(espera)
                continue
            return resultado

        return resultado

    return {"erro": "Falha inesperada no retry do Gemini", "raw": ""}


def parse_data_limit_submissao(raw_value: str | None) -> datetime | None:
    raw = (raw_value or "").strip()
    if not raw:
        return None

    # formato esperado da IA: yyyy-mm-dd
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        # fallback defensivo para dd/mm/yyyy
        try:
            parsed = datetime.strptime(raw, "%d/%m/%Y")
        except ValueError:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


def run_pipeline(source_key: str | None = None, limit: int | None = LIMIT):
    source_id, source = get_source_config(source_key)

    links = source["collect_links"](source["base_url"])
    if not links:
        print(f"Nenhum PDF encontrado para a fonte {source['label']}.")
        return

    links = links if limit is None else links[:limit]

    print(
        f"Fonte: {source['label']} ({source_id}) | "
        f"Collection Mongo: {source['mongo_collection']}"
    )
    print(f"{len(links)} PDFs para processar.\n")

    for i, link in enumerate(links, start=1):
        if already_exists(link, collection_name=source["mongo_collection"]):
            print(f"[{i}/{len(links)}] ✅ Já salvo no MongoDB (status=ok): {link}")
            if i < len(links):
                time.sleep(SLEEP_ALREADY_EXISTS)
            continue

        print(f"[{i}/{len(links)}] 📄 {link}")
        texto = extract_text_from_pdf_url(link)

        if not texto:
            print("Texto vazio.\n")
            status = save(
                link,
                {"erro": "Texto vazio"},
                texto_preview="",
                collection_name=source["mongo_collection"],
                data_limit_submissao=None,
            )
            if status != "disabled":
                print(f"💾 MongoDB: {status}")
            if i < len(links):
                time.sleep(SLEEP_EMPTY_TEXT)
            continue

        resultado = retry_analyze_text(texto, link)
        data_limit_submissao = parse_data_limit_submissao(
            resultado.get("data_limit_submissao")
        )

        status = save(
            link,
            resultado,
            texto_preview=texto,
            collection_name=source["mongo_collection"],
            data_limit_submissao=data_limit_submissao,
        )

        if status != "disabled":
            print(f"💾 MongoDB: {status}")

        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        print("\n" + "-" * 60 + "\n")

        if i < len(links):
            time.sleep(SLEEP_NEW_PROCESS)


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()

    try:
        run_pipeline(source_key=args.source, limit=parse_limit(args.limit))
    except ValueError as exc:
        print(exc)