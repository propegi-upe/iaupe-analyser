from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# garante que a raiz do projeto esteja no pythonpath para importar "pipeline"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.emails.gmail_smtp_email_service import GmailSmtpEmailService
from pipeline.emails.send_email_use_case import SendEmailUseCase
from pipeline.pdf_pipeline.analyzer import analyze_text
from pipeline.pdf_pipeline.extractor import extract_text_from_pdf_url
from pipeline.sources import scraper_capes, scraper_cnpq, scraper_facepe, scraper_finep


SOURCE_REGISTRY = {
    scraper_facepe.SOURCE_KEY: {
        "label": scraper_facepe.SOURCE_LABEL,
        "base_url": scraper_facepe.BASE_URL,
        "collect_links": scraper_facepe.collect_links,
    },
    scraper_cnpq.SOURCE_KEY: {
        "label": scraper_cnpq.SOURCE_LABEL,
        "base_url": scraper_cnpq.BASE_URL,
        "collect_links": scraper_cnpq.collect_links,
    },
    scraper_finep.SOURCE_KEY: {
        "label": scraper_finep.SOURCE_LABEL,
        "base_url": scraper_finep.BASE_URL,
        "collect_links": scraper_finep.collect_links,
    },
    scraper_capes.SOURCE_KEY: {
        "label": scraper_capes.SOURCE_LABEL,
        "base_url": scraper_capes.BASE_URL,
        "collect_links": scraper_capes.collect_links,
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Teste de fluxo edital -> json -> email (Mailtrap)"
    )
    parser.add_argument(
        "--source",
        default=(os.getenv("PIPELINE_SOURCE") or "facepe").strip().lower(),
        choices=sorted(SOURCE_REGISTRY),
        help="Fonte para coletar um edital real",
    )
    parser.add_argument(
        "--pdf-url",
        default="",
        help="URL direta de PDF (se informada, ignora --source)",
    )
    parser.add_argument(
        "--to",
        default=(os.getenv("TEST_EMAIL_TO") or "to@example.com").strip(),
        help="Destinatario do email de teste",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="Numero maximo de paginas para extrair do PDF",
    )
    return parser


def resolve_pdf_url(source_key: str, explicit_pdf_url: str) -> tuple[str, str]:
    if explicit_pdf_url.strip():
        return explicit_pdf_url.strip(), "url-manual"

    source = SOURCE_REGISTRY[source_key]
    links = source["collect_links"](source["base_url"])
    if not links:
        raise RuntimeError(f"Nenhum PDF encontrado para a fonte {source['label']}")

    return links[0], source["label"]


def format_items(items: list[str], empty_label: str) -> list[str]:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if not cleaned:
        return [f"- {empty_label}"]
    return [f"- {item}" for item in cleaned]


def main() -> None:
    load_dotenv(override=True)
    args = build_parser().parse_args()

    pdf_url, source_label = resolve_pdf_url(args.source, args.pdf_url)
    print(f"fonte selecionada: {source_label}")
    print(f"pdf usado no teste: {pdf_url}")

    texto = extract_text_from_pdf_url(pdf_url, max_pages=args.max_pages)
    if not texto:
        resultado = {"url_pdf": pdf_url, "erro": "Texto vazio"}
    else:
        resultado = analyze_text(texto, pdf_url)

    subject_prefix = "ok" if "erro" not in resultado else "erro"
    subject = f"[teste-iaupe] {subject_prefix} | {source_label}"

    # monta um relatorio padronizado para leitura humana no email
    areas = resultado.get("areas_interesse") or []
    segmentos = resultado.get("segmentos") or []
    cronograma = resultado.get("cronograma") or []
    criterios_publico = resultado.get("criterios_publico_alvo") or []
    criterios_proponente = resultado.get("criterios_proponente") or []
    observacoes = resultado.get("observacoes") or []
    publico_alvo = (resultado.get("publico_alvo") or "").strip()
    descricao = (resultado.get("descricao") or "").strip()
    status = "erro" if "erro" in resultado else "ok"

    relatorio_linhas = [
        "relatorio padronizado de edital",
        "",
        "[identificacao]",
        f"fonte: {source_label}",
        f"status: {status}",
        f"url_pdf: {resultado.get('url_pdf', pdf_url)}",
        "",
        "[resumo]",
        f"publico_alvo: {publico_alvo[:500] if publico_alvo else 'nao informado'}",
        f"descricao: {descricao[:500] if descricao else 'nao informado'}",
        "",
        "[classificacao]",
        f"areas_interesse_total: {len(areas)}",
        *format_items(areas, "nenhuma area classificada"),
        "",
        f"segmentos_total: {len(segmentos)}",
        *format_items(segmentos, "nenhum segmento classificado"),
        "",
        "[criterios_publico_alvo]",
        *format_items(criterios_publico, "nao informado"),
        "",
        "[criterios_proponente]",
        *format_items(criterios_proponente, "nao informado"),
        "",
        "[observacoes]",
        *format_items(observacoes, "nao informado"),
        "",
        "[cronograma]",
        f"itens_cronograma_total: {len(cronograma)}",
        *format_items(cronograma, "nao informado"),
    ]

    body = "\n".join(relatorio_linhas)

    use_case = SendEmailUseCase(GmailSmtpEmailService())
    use_case.execute(
        {
            "to": args.to,
            "subject": subject,
            "text": body,
        }
    )

    print("email de fluxo enviado com relatorio padronizado")


if __name__ == "__main__":
    main()
