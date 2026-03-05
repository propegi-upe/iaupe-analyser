from dotenv import load_dotenv
import os
import sys
from pathlib import Path
from pymongo import MongoClient

# Garante que a raiz do meu projeto esteja no PYTHONPATH (para importar "pipeline")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.services.scraper import collect_facepe_pdf_links

load_dotenv(override=True)


URL_FACEPE = "https://www.facepe.br/editais/todos/?c=aberto"

def main():
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB", "iaupe-analyser")
    coll_name = os.getenv("MONGODB_COLLECTION", "editais")

    if not uri:
        raise RuntimeError("MONGODB_URI não definido no .env")

    client = MongoClient(uri)
    coll = client[db_name][coll_name]

    links = collect_facepe_pdf_links(URL_FACEPE)
    total_links = len(links)

    found = coll.count_documents({"url_pdf": {"$in": links}})
    ok = coll.count_documents({"url_pdf": {"$in": links}, "status": "ok"})
    erro = coll.count_documents({"url_pdf": {"$in": links}, "status": "erro"})

    print("DB:", db_name)
    print("Collection:", coll_name)
    print("Links no site:", total_links)
    print("Docs no Mongo p/ esses links:", found)
    print(" - status=ok:", ok)
    print(" - status=erro:", erro)
    print("Faltando:", total_links - found)

    if found < total_links:
        existing = set(
            doc["url_pdf"]
            for doc in coll.find({"url_pdf": {"$in": links}}, {"_id": 0, "url_pdf": 1})
        )

        missing = [u for u in links if u not in existing]
        print("\nExemplos de links faltando (até 50):")
        for u in missing[:50]:
            print("-", u)

if __name__ == "__main__":
    main()