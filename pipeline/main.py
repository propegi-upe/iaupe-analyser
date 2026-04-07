import argparse
import os
from orchestration.pipeline_runner import run_pipeline
from orchestration.settings import parse_limit
from orchestration.source_registry import DEFAULT_SOURCE, SOURCE_REGISTRY


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


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()

    try:
        run_pipeline(source_key=args.source, limit=parse_limit(args.limit))
    except ValueError as exc:
        print(exc)