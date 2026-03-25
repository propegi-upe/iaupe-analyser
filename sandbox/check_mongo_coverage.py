from dotenv import load_dotenv
import argparse
import os
import sys
from pathlib import Path

import certifi
from pymongo import MongoClient

# Garante que a raiz do projeto esteja no PYTHONPATH (para importar "pipeline")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.sources import scraper_capes, scraper_cnpq, scraper_facepe, scraper_finep

load_dotenv(override=True)

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


def _get_source_config(source_key: str) -> tuple[str, dict]:
    selected_key = (source_key or DEFAULT_SOURCE).strip().lower()
    source = SOURCE_REGISTRY.get(selected_key)
    if source is None:
        disponiveis = ", ".join(sorted(SOURCE_REGISTRY))
        raise ValueError(f"Fonte invalida: {selected_key!r}. Opcoes: {disponiveis}")
    return selected_key, source


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Checagem de cobertura no MongoDB por fonte"
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help=f"Fonte alvo ({', '.join(sorted(SOURCE_REGISTRY))})",
    )
    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    source_id, source = _get_source_config(args.source)

    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB", "iaupe-analyser")
    coll_name = source["mongo_collection"]

    if not uri:
        raise RuntimeError("MONGODB_URI nao definido no .env")

    client = MongoClient(uri, tlsCAFile=certifi.where())
    coll = client[db_name][coll_name]

    links = source["collect_links"](source["base_url"])
    total_links = len(links)

    print("Fonte:", f"{source['label']} ({source_id})")
    print("DB:", db_name)
    print("Collection:", coll_name)
    print("Links no site:", total_links)

    if total_links == 0:
        print("Nenhum link coletado para essa fonte.")
        return

    found = coll.count_documents({"url_pdf": {"$in": links}})
    ok = coll.count_documents({"url_pdf": {"$in": links}, "status": "ok"})
    erro = coll.count_documents({"url_pdf": {"$in": links}, "status": "erro"})

    print("Docs no Mongo p/ esses links:", found)
    print(" - status=ok:", ok)
    print(" - status=erro:", erro)
    print("Faltando:", total_links - found)
    
    print("\nLinks coletados (em ordem):")
    for i, u in enumerate(links, start=1):
        print(f"[{i}/{total_links}] {u}")

if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(exc)