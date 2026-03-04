import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

load_dotenv(override=True)

_client: Optional[MongoClient] = None
_collection: Optional[Collection] = None


def _coll() -> Collection:
    """
    Retorna a collection do MongoDB (com cache) e garante índice único por `url_pdf`.
    """
    global _client, _collection

    if _collection is not None:
        return _collection

    uri = (os.getenv("MONGODB_URI") or "").strip()
    if not uri:
        raise RuntimeError("Defina MONGODB_URI no .env")

    db_name = (os.getenv("MONGODB_DB") or "iaupe-analyser").strip()
    coll_name = (os.getenv("MONGODB_COLLECTION") or "editais").strip()

    _client = MongoClient(uri)
    _collection = _client[db_name][coll_name]

    # evita analisar/salvar o mesmo PDF várias vezes
    _collection.create_index([("url_pdf", ASCENDING)], unique=True)

    return _collection


def ja_existe(url_pdf: str) -> bool:
    doc = _coll().find_one({"url_pdf": url_pdf}, {"_id": 1, "status": 1})
    return bool(doc) and doc.get("status") == "ok"


def salvar(url_pdf: str, resultado: dict, texto_preview: Optional[str] = None) -> str:
    now = datetime.now(timezone.utc)

    doc_set = {
        "url_pdf": url_pdf,
        "resultado": resultado,
        "status": "ok" if "erro" not in (resultado or {}) else "erro",
        "updated_at": now,
    }
    if texto_preview is not None:
        doc_set["texto_preview"] = texto_preview[:2000]

    try:
        _coll().insert_one({**doc_set, "created_at": now})
        return "inserted"
    except DuplicateKeyError:
        _coll().update_one({"url_pdf": url_pdf}, {"$set": doc_set})
        return "updated"