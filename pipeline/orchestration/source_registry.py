import os

from sources import scraper_capes, scraper_cnpq, scraper_facepe, scraper_finep

# catalogo central de fontes suportadas pela pipeline
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


def get_source_config(source_key: str | None) -> tuple[str, dict]:
    """
    Resolve a configuracao da fonte selecionada.

    Retorna (source_key_normalizada, configuracao_da_fonte).
    """
    selected_key = (source_key or DEFAULT_SOURCE).strip().lower()
    source = SOURCE_REGISTRY.get(selected_key)
    if source is None:
        disponiveis = ", ".join(sorted(SOURCE_REGISTRY))
        raise ValueError(f"Fonte invalida: {selected_key!r}. Opcoes: {disponiveis}")
    return selected_key, source
