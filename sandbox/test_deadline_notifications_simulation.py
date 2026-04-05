from __future__ import annotations

import argparse
import os
import smtplib
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# garante que a raiz do projeto esteja no pythonpath para importar "pipeline"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.emails.gmail_smtp_email_service import GmailSmtpEmailService
from pipeline.emails.send_email_use_case import SendEmailUseCase

DEFAULT_STEPS = [3, 2, 1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simula notificacoes de prazo no marco exato (ex: 3,2,1 dias)"
    )
    parser.add_argument(
        "--start-date",
        default="",
        help="Data inicial da simulacao (YYYY-MM-DD). Ex: 2026-04-04",
    )
    parser.add_argument(
        "--deadline",
        default="",
        help="Data limite de submissao (YYYY-MM-DD). Ex: 2026-04-07",
    )
    parser.add_argument(
        "--days",
        nargs="+",
        type=int,
        default=DEFAULT_STEPS,
        help="Marcos da simulacao. Ex: 3 2 1",
    )
    parser.add_argument(
        "--to",
        default=(os.getenv("TEST_EMAIL_TO") or "to@example.com").strip(),
        help="Destinatario para o envio",
    )
    parser.add_argument(
        "--url-pdf",
        default="https://exemplo.local/edital-teste.pdf",
        help="URL fake do edital para identificar o teste",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Envia email; sem essa flag roda em dry-run",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.5,
        help="Intervalo entre envios para evitar limite de taxa do SMTP",
    )
    return parser


def parse_iso_date(raw: str, field_name: str) -> date:
    try:
        return datetime.fromisoformat(raw.strip()).date()
    except ValueError as exc:
        raise ValueError(f"{field_name} invalido. Use YYYY-MM-DD") from exc


def resolve_dates(start_raw: str, deadline_raw: str) -> tuple[date, date]:
    start = parse_iso_date(start_raw, "--start-date") if start_raw.strip() else None
    deadline = parse_iso_date(deadline_raw, "--deadline") if deadline_raw.strip() else None

    if start and deadline:
        return start, deadline

    if start and not deadline:
        # padrao para o exemplo pedido: se comeca no dia 4 e quer 3,2,1
        # o prazo fica 3 dias apos a data inicial
        return start, start + timedelta(days=3)

    if deadline and not start:
        # se so informou o prazo, inicia 3 dias antes
        return deadline - timedelta(days=3), deadline

    # sem parametros, gera um caso totalmente deterministico para teste rapido
    default_start = date(2026, 4, 4)
    default_deadline = date(2026, 4, 7)
    return default_start, default_deadline


def build_body(simulation_date: date, deadline: date, days_left: int, pdf_url: str) -> str:
    return "\n".join(
        [
            "notificacao de teste de prazo (simulacao)",
            "",
            f"data simulada de execucao: {simulation_date.isoformat()}",
            f"prazo final do edital: {deadline.isoformat()}",
            f"faltam: {days_left} dia(s)",
            f"url_pdf: {pdf_url}",
        ]
    )


def is_mailtrap_rate_limit(exc: smtplib.SMTPDataError) -> bool:
    message = str(exc).lower()
    return exc.smtp_code == 550 and "too many emails per second" in message


def send_with_retry(
    use_case: SendEmailUseCase,
    payload: dict,
    sleep_seconds: float,
    retry_backoff_seconds: list[float],
) -> None:
    attempts = [max(sleep_seconds, 0.0)] + retry_backoff_seconds

    for attempt_idx, wait_seconds in enumerate(attempts, start=1):
        try:
            use_case.execute(payload)
            return
        except smtplib.SMTPDataError as exc:
            if not is_mailtrap_rate_limit(exc) or attempt_idx == len(attempts):
                raise

            print(
                f"rate limit do smtp detectado (tentativa {attempt_idx}/{len(attempts)}). "
                f"aguardando {wait_seconds}s para tentar novamente..."
            )
            time.sleep(wait_seconds)


def main() -> None:
    load_dotenv(override=True)
    args = build_parser().parse_args()

    start_date, deadline = resolve_dates(args.start_date, args.deadline)
    days_targets = set(args.days)

    print(f"inicio simulacao: {start_date.isoformat()}")
    print(f"prazo final: {deadline.isoformat()}")
    print(f"marcos alvo: {sorted(days_targets)}")
    print(f"modo envio: {'send' if args.send else 'dry-run'}")

    use_case = SendEmailUseCase(GmailSmtpEmailService()) if args.send else None
    retry_backoff_seconds = [5.0, 10.0, 20.0]

    # simula dias consecutivos ate o dia anterior ao prazo
    simulation_date = start_date
    notifications = 0

    while simulation_date < deadline:
        days_left = (deadline - simulation_date).days

        if days_left in days_targets:
            subject = (
                f"[teste-iaupe] marco exato: faltam {days_left} dia(s) "
                f"| prazo {deadline.isoformat()}"
            )
            body = build_body(simulation_date, deadline, days_left, args.url_pdf)

            if args.send and use_case is not None:
                payload = {
                    "to": args.to,
                    "subject": subject,
                    "text": body,
                }
                send_with_retry(
                    use_case,
                    payload,
                    sleep_seconds=max(args.sleep_seconds, 0.0),
                    retry_backoff_seconds=retry_backoff_seconds,
                )
                print(
                    f"email enviado -> data_simulada={simulation_date.isoformat()} | faltam={days_left}"
                )
                time.sleep(max(args.sleep_seconds, 0.0))
            else:
                print(
                    f"dry-run -> data_simulada={simulation_date.isoformat()} | faltam={days_left}"
                )
                print(body)
                print("-" * 60)

            notifications += 1

        simulation_date += timedelta(days=1)

    print(f"notificacoes geradas: {notifications}")


if __name__ == "__main__":
    main()
