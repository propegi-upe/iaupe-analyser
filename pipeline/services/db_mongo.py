import os
from datetime import datetime, timezone
from typing import Optional

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

load_dotenv(override=True)

_client: Optional[MongoClient] = None
_collection: Optional[Collection] = None
_mongo_disabled = False
_mongo_disable_reason: Optional[str] = None


def _disable_mongo(reason: str) -> None:
    global _mongo_disabled, _mongo_disable_reason

    if _mongo_disabled:
        return

    _mongo_disabled = True
    _mongo_disable_reason = reason
    print(f"[MongoDB] Persistencia desabilitada: {reason}")


def _mongo_is_requested() -> bool:
    raw_value = (os.getenv("MONGODB_ENABLED") or "auto").strip().lower()
    if raw_value in {"0", "false", "no", "off", "disabled"}:
        return False

    uri = (os.getenv("MONGODB_URI") or "").strip()
    return bool(uri)


def _coll() -> Collection:
    """
    Retorna a collection do MongoDB (com cache) e garante índice único por `url_pdf`.
    """
    global _client, _collection

    if _collection is not None:
        return _collection

    if _mongo_disabled or not _mongo_is_requested():
        raise RuntimeError(_mongo_disable_reason or "MongoDB desabilitado ou nao configurado")

    uri = (os.getenv("MONGODB_URI") or "").strip()
    db_name = (os.getenv("MONGODB_DB") or "iaupe-analyser").strip()
    coll_name = (os.getenv("MONGODB_COLLECTION") or "editais").strip()

    server_selection_timeout_ms = int(
        (os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS") or "30000").strip()
    )
    connect_timeout_ms = int(
        (os.getenv("MONGODB_CONNECT_TIMEOUT_MS") or "30000").strip()
    )
    socket_timeout_ms = int(
        (os.getenv("MONGODB_SOCKET_TIMEOUT_MS") or "30000").strip()
    )

    try:
        _client = MongoClient(
            uri,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=server_selection_timeout_ms,
            connectTimeoutMS=connect_timeout_ms,
            socketTimeoutMS=socket_timeout_ms,
            retryWrites=True,
        )
        _collection = _client[db_name][coll_name]

        _collection.create_index([("url_pdf", ASCENDING)], unique=True)

    except PyMongoError as exc:
        _client = None
        _collection = None
        _disable_mongo(str(exc))
        raise RuntimeError(_mongo_disable_reason or "Falha ao conectar no MongoDB") from exc

    return _collection


def already_exists(url_pdf: str) -> bool:
    try:
        doc = _coll().find_one({"url_pdf": url_pdf}, {"_id": 1, "status": 1})
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao consultar already_exists: {exc}")
        return False

    return bool(doc) and doc.get("status") == "ok"


def save(url_pdf: str, resultado: dict, texto_preview: Optional[str] = None) -> str:
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
        try:
            _coll().update_one({"url_pdf": url_pdf}, {"$set": doc_set})
            return "updated"
        except (RuntimeError, PyMongoError) as exc:
            print(f"[MongoDB] Falha ao atualizar documento duplicado: {exc}")
            return "disabled"

    except RuntimeError:
        return "disabled"

    except PyMongoError as exc:
        _disable_mongo(str(exc))
        return "disabled"