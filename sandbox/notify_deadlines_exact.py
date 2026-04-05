from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient

# garante que a raiz do projeto esteja no pythonpath para importar "pipeline"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.emails.gmail_smtp_email_service import GmailSmtpEmailService
from pipeline.emails.send_email_use_case import SendEmailUseCase
from pipeline.sources import scraper_capes, scraper_cnpq, scraper_facepe, scraper_finep

SOURCE_REGISTRY = {
    scraper_facepe.SOURCE_KEY: {
        "label": scraper_facepe.SOURCE_LABEL,
        "mongo_collection": scraper_facepe.MONGO_COLLECTION,
    },
    scraper_cnpq.SOURCE_KEY: {
        "label": scraper_cnpq.SOURCE_LABEL,
        "mongo_collection": scraper_cnpq.MONGO_COLLECTION,
    },
    scraper_finep.SOURCE_KEY: {
        "label": scraper_finep.SOURCE_LABEL,
        "mongo_collection": scraper_finep.MONGO_COLLECTION,
    },
    scraper_capes.SOURCE_KEY: {
        "label": scraper_capes.SOURCE_LABEL,
        "mongo_collection": scraper_capes.MONGO_COLLECTION,
    },
}

DEFAULT_SOURCE = (os.getenv("PIPELINE_SOURCE") or "facepe").strip().lower()
DEFAULT_DAYS = [30, 15, 7]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Notifica editais com prazo no marco exato (30/15/7 dias)"
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        choices=sorted(SOURCE_REGISTRY),
        help="Fonte alvo",
    )
    parser.add_argument(
        "--to",
        default=(os.getenv("TEST_EMAIL_TO") or "to@example.com").strip(),
        help="Destinatario para o email de notificacao",
    )
    parser.add_argument(
        "--days",
        nargs="+",
        type=int,
        default=DEFAULT_DAYS,
        help="Marcos de notificacao em dias (ex: 30 15 7)",
    )
    parser.add_argument(
        "--today",
        default="",
        help="Data de referencia YYYY-MM-DD (se vazio, usa hoje em UTC)",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Envia email; sem essa flag roda em dry-run",
    )
    return parser


def parse_today(raw_today: str) -> date:
    raw = raw_today.strip()
    if raw:
        return datetime.fromisoformat(raw).date()
    return datetime.now(timezone.utc).date()


def normalize_datetime_utc(value: datetime) -> datetime:
    # no pymongo, datetimes podem vir sem tzinfo; tratamos como utc
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def format_notification_lines(matches: list[dict], source_label: str, today: date) -> str:
    lines = [
        "notificacao de prazo de submissao (marco exato)",
        "",
        f"fonte: {source_label}",
        f"data de referencia: {today.isoformat()}",
        "",
        "editais com prazo no marco:",
    ]

    for item in matches:
        lines.append(
            f"- faltam {item['days_left']} dias | prazo: {item['deadline']} | url: {item['url_pdf']}"
        )
        if item["descricao"]:
            lines.append(f"  descricao: {item['descricao']}")

    return "\n".join(lines)


def main() -> None:
    load_dotenv(override=True)
    args = build_parser().parse_args()

    uri = (os.getenv("MONGODB_URI") or "").strip()
    db_name = (os.getenv("MONGODB_DB") or "iaupe-analyser").strip()

    if not uri:
        raise RuntimeError("MONGODB_URI nao definido no .env")

    source = SOURCE_REGISTRY[args.source]
    source_label = source["label"]
    coll_name = source["mongo_collection"]

    today = parse_today(args.today)
    days_targets = set(args.days)

    client = MongoClient(uri, tlsCAFile=certifi.where())
    coll = client[db_name][coll_name]

    cursor = coll.find(
        {
            "status": "ok",
            "data_limit_submissao": {"$exists": True, "$ne": None},
        },
        {
            "_id": 0,
            "url_pdf": 1,
            "data_limit_submissao": 1,
            "resultado.descricao": 1,
        },
    )

    matches: list[dict] = []
    for doc in cursor:
        deadline = doc.get("data_limit_submissao")
        if not isinstance(deadline, datetime):
            continue

        deadline_date = normalize_datetime_utc(deadline).date()
        days_left = (deadline_date - today).days

        if days_left not in days_targets:
            continue

        descricao = str((doc.get("resultado") or {}).get("descricao") or "").strip()
        if len(descricao) > 160:
            descricao = descricao[:160] + "..."

        matches.append(
            {
                "url_pdf": str(doc.get("url_pdf") or "").strip(),
                "days_left": days_left,
                "deadline": deadline_date.isoformat(),
                "descricao": descricao,
            }
        )

    matches.sort(key=lambda item: (item["days_left"], item["deadline"], item["url_pdf"]))

    print(f"fonte: {source_label} ({args.source})")
    print(f"collection: {coll_name}")
    print(f"data de referencia: {today.isoformat()}")
    print(f"marcos alvo: {sorted(days_targets)}")
    print(f"notificacoes encontradas: {len(matches)}")

    if not matches:
        print("nenhum edital bateu no marco exato")
        return

    body = format_notification_lines(matches, source_label, today)
    subject = f"[iaupe] prazo de submissao proximo ({','.join(map(str, sorted(days_targets)))}) | {source_label}"

    if not args.send:
        print("\n(dry-run) email nao enviado. use --send para enviar.\n")
        print(body)
        return

    use_case = SendEmailUseCase(GmailSmtpEmailService())
    use_case.execute(
        {
            "to": args.to,
            "subject": subject,
            "text": body,
        }
    )
    print(f"email enviado para: {args.to}")


if __name__ == "__main__":
    main()
