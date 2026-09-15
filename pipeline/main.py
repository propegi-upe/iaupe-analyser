import argparse
import logging
import os
import sys
from db.interessados import add_interessado, list_interessados, remove_interessado
from orchestration.deadline_reminder_runner import run_deadline_reminders
from orchestration.docente_notification_service import DEFAULT_MAX_EMAILS, DEFAULT_MAX_POR_DOCENTE
from orchestration.new_edital_notify_runner import run_new_edital_notifications
from orchestration.pipeline_runner import run_pipeline
from orchestration.settings import parse_limit
from orchestration.source_registry import DEFAULT_SOURCE, SOURCE_REGISTRY


def build_parser() -> argparse.ArgumentParser:
    """
    Monta o parser da CLI principal da pipeline.

    Parametros:
    - --source: fonte de editais (facepe, cnpq, finep, capes)
    - --limit: limite de PDFs processados na execucao
    """
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
    parser.add_argument(
        "--run-reminders",
        action="store_true",
        help="Executa somente notificacoes de prazo (D-30, D-15, D-7)",
    )
    parser.add_argument(
        "--reminder-steps",
        default=os.getenv("DEADLINE_REMINDER_STEPS") or "30,15,7",
        help="Marcos de lembrete separados por virgula. Ex: 30,15,7",
    )
    parser.add_argument(
        "--notify-editais",
        action="store_true",
        help=(
            "Simula a notificacao de docentes sobre editais ja salvos que casam com as "
            "areas/segmentos deles e ainda nao foram avisados (backfill). "
            "Use --source all para todas as fontes e --apply para enviar de verdade"
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Com --notify-editais: envia de verdade (sem isso e so simulacao)",
    )
    parser.add_argument(
        "--max-por-docente",
        type=int,
        default=DEFAULT_MAX_POR_DOCENTE,
        help=(
            "Com --notify-editais: maximo de e-mails para a MESMA pessoa numa execucao "
            f"(padrao {DEFAULT_MAX_POR_DOCENTE}). O resto fica para a proxima rodada"
        ),
    )
    parser.add_argument(
        "--max-emails",
        type=int,
        default=DEFAULT_MAX_EMAILS,
        help=(
            "Com --notify-editais: maximo de e-mails no total por execucao "
            f"(padrao {DEFAULT_MAX_EMAILS})"
        ),
    )
    parser.add_argument(
        "--url",
        metavar="URL_PDF",
        help="URL do PDF do edital (usado com --add-interessado/--remove-interessado/--list-interessados)",
    )
    parser.add_argument(
        "--email",
        metavar="EMAIL",
        help="E-mail da pessoa (usado com --add-interessado/--remove-interessado)",
    )
    parser.add_argument(
        "--add-interessado",
        action="store_true",
        help="Inscreve --email no edital --url",
    )
    parser.add_argument(
        "--remove-interessado",
        action="store_true",
        help="Remove --email do edital --url",
    )
    parser.add_argument(
        "--list-interessados",
        action="store_true",
        help="Lista os e-mails inscritos no edital --url",
    )
    return parser


if __name__ == "__main__":
    # entrypoint da pipeline de producao
    # sem isso, logger.info/warning/error configurados nos modulos abaixo
    # (ex.: orchestration/docente_notification_service.py) nao aparecem no
    # log do GitHub Actions - so o "lastResort" handler do Python mostra
    # WARNING/ERROR por padrao.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stdout)

    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.add_interessado or args.remove_interessado or args.list_interessados:
            # fluxo de interessados: inscrever/remover/listar e-mails por edital
            # especifico. A collection e unica, entao basta a url_pdf (nao
            # precisa mais saber de qual fonte o edital veio).
            if not args.url:
                print("Informe --url com a URL do PDF do edital.")
                raise SystemExit(1)

            if args.add_interessado:
                if not args.email:
                    print("Informe --email para inscrever.")
                    raise SystemExit(1)
                status = add_interessado(args.url, args.email)
                print(f"Inscrever interessado: {status} -> {args.email}")

            if args.remove_interessado:
                if not args.email:
                    print("Informe --email para remover.")
                    raise SystemExit(1)
                status = remove_interessado(args.url, args.email)
                print(f"Remover interessado: {status} -> {args.email}")

            if args.list_interessados:
                emails = list_interessados(args.url)
                print(f"Interessados em {args.url} ({len(emails)}):")
                for email in emails:
                    print(f"- {email}")
        elif args.notify_editais:
            # varredura avulsa; no dia a dia a propria pipeline ja notifica ao
            # salvar cada edital novo (ver orchestration/pipeline_runner.py).
            run_new_edital_notifications(
                source_key=args.source,
                apply=args.apply,
                max_por_docente=args.max_por_docente,
                max_emails=args.max_emails,
            )
        elif args.run_reminders:
            run_deadline_reminders(
                source_key=args.source,
                steps_raw=args.reminder_steps,
            )
        else:
            # delega a orquestracao para o runner
            run_pipeline(source_key=args.source, limit=parse_limit(args.limit))
    except ValueError as exc:
        # erros de validacao de parametros/fonte
        print(exc)
    except Exception as exc:
        # erros inesperados da execucao da pipeline
        print(f"Erro inesperado na execucao da pipeline: {exc}")