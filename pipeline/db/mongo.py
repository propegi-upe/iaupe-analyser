import os
from datetime import datetime, timezone
from typing import Optional

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

load_dotenv(override=True)

client_cache: Optional[MongoClient] = None
collection_cache: dict[str, Collection] = {}
mongo_disabled = False
mongo_disable_reason: Optional[str] = None


def disable_mongo(reason: str) -> None:
    """Desabilita persistencia no Mongo apos falha critica de conexao."""
    global mongo_disabled, mongo_disable_reason

    if mongo_disabled:
        return

    mongo_disabled = True
    mongo_disable_reason = reason
    print(f"[MongoDB] Persistencia desabilitada: {reason}")


def mongo_is_requested() -> bool:
    """Define se o Mongo deve ser usado com base em env vars."""
    raw_value = (os.getenv("MONGODB_ENABLED") or "auto").strip().lower()
    if raw_value in {"0", "false", "no", "off", "disabled"}:
        return False

    uri = (os.getenv("MONGODB_URI") or "").strip()
    return bool(uri)


def resolve_collection_name(collection_name: Optional[str]) -> str:
    """Resolve nome da collection com fallback para configuracao global."""
    resolved = (collection_name or os.getenv("MONGODB_COLLECTION") or "editais").strip()
    return resolved or "editais"


def coll(collection_name: Optional[str] = None) -> Collection:
    """
    Retorna a collection do MongoDB (com cache) e garante indice unico por url_pdf.
    """
    global client_cache, collection_cache

    coll_name = resolve_collection_name(collection_name)

    if coll_name in collection_cache:
        return collection_cache[coll_name]

    if mongo_disabled or not mongo_is_requested():
        raise RuntimeError(mongo_disable_reason or "MongoDB desabilitado ou nao configurado")

    uri = (os.getenv("MONGODB_URI") or "").strip()
    db_name = (os.getenv("MONGODB_DB") or "iaupe-analyser").strip()
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
        # cria cliente apenas uma vez e reaproveita nas chamadas seguintes
        if client_cache is None:
            client_cache = MongoClient(
                uri,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=server_selection_timeout_ms,
                connectTimeoutMS=connect_timeout_ms,
                socketTimeoutMS=socket_timeout_ms,
                retryWrites=True,
            )

        # cache da collection por nome para reduzir overhead
        collection = client_cache[db_name][coll_name]
        collection.create_index([("url_pdf", ASCENDING)], unique=True)
        collection_cache[coll_name] = collection

    except PyMongoError as exc:
        client_cache = None
        collection_cache = {}
        disable_mongo(str(exc))
        raise RuntimeError(mongo_disable_reason or "Falha ao conectar no MongoDB") from exc

    return collection_cache[coll_name]


def     already_exists(url_pdf: str, collection_name: Optional[str] = None) -> bool:
    """Verifica se um edital ja foi salvo com status ok."""
    try:
        doc = coll(collection_name).find_one({"url_pdf": url_pdf}, {"_id": 1, "status": 1})
    except (RuntimeError, PyMongoError) as exc:
        print(f"[MongoDB] Falha ao consultar already_exists: {exc}")
        return False

    return bool(doc) and doc.get("status") == "ok"


def save(
    url_pdf: str,
    resultado: dict,
    texto_preview: Optional[str] = None,
    collection_name: Optional[str] = None,
    data_limit_submissao: Optional[datetime] = None,
) -> str:
    """
    Persiste (insert/update) o resultado da analise de um edital.

    Retorna: inserted | updated | disabled
    """
    now = datetime.now(timezone.utc)

    doc_set = {
        "url_pdf": url_pdf,
        "resultado": resultado,
        "status": "ok" if "erro" not in (resultado or {}) else "erro",
        "data_limit_submissao": data_limit_submissao,
        "updated_at": now,
    }

    if texto_preview is not None:
        doc_set["texto_preview"] = texto_preview[:2000]

    try:
        # insert preferencial para manter created_at apenas na primeira gravacao
        collection = coll(collection_name)
        collection.insert_one({**doc_set, "created_at": now})
        return "inserted"

    except DuplicateKeyError:
        # se ja existe url_pdf, atualiza campos mutaveis
        try:
            collection = coll(collection_name)
            collection.update_one({"url_pdf": url_pdf}, {"$set": doc_set})
            return "updated"
        except (RuntimeError, PyMongoError) as exc:
            print(f"[MongoDB] Falha ao atualizar documento duplicado: {exc}")
            return "disabled"

    except RuntimeError:
        return "disabled"

    except PyMongoError as exc:
        disable_mongo(str(exc))
        return "disabled"
