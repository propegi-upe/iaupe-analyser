import json
import time

from db.mongo import already_exists, save
from pdf_pipeline.extractor import extract_text_from_pdf_url
from .date_parser import parse_data_limit_submissao
from .retry_policy import retry_analyze_text
from .settings import LIMIT, SLEEP_ALREADY_EXISTS, SLEEP_EMPTY_TEXT, SLEEP_NEW_PROCESS
from .source_registry import get_source_config


def run_pipeline(source_key: str | None = None, limit: int | None = LIMIT) -> None:
    source_id, source = get_source_config(source_key)

    links = source["collect_links"](source["base_url"])
    if not links:
        print(f"Nenhum PDF encontrado para a fonte {source['label']}.")
        return

    links = links if limit is None else links[:limit]

    print(
        f"Fonte: {source['label']} ({source_id}) | "
        f"Collection Mongo: {source['mongo_collection']}"
    )
    print(f"{len(links)} PDFs para processar.\n")

    for i, link in enumerate(links, start=1):
        if already_exists(link, collection_name=source["mongo_collection"]):
            print(f"[{i}/{len(links)}] ✅ Já salvo no MongoDB (status=ok): {link}")
            if i < len(links):
                time.sleep(SLEEP_ALREADY_EXISTS)
            continue

        print(f"[{i}/{len(links)}] 📄 {link}")
        texto = extract_text_from_pdf_url(link)

        if not texto:
            print("Texto vazio.\n")
            status = save(
                link,
                {"erro": "Texto vazio"},
                texto_preview="",
                collection_name=source["mongo_collection"],
                data_limit_submissao=None,
            )
            if status != "disabled":
                print(f"💾 MongoDB: {status}")
            if i < len(links):
                time.sleep(SLEEP_EMPTY_TEXT)
            continue

        resultado = retry_analyze_text(texto, link)
        data_limit_submissao = parse_data_limit_submissao(
            resultado.get("data_limit_submissao")
        )

        status = save(
            link,
            resultado,
            texto_preview=texto,
            collection_name=source["mongo_collection"],
            data_limit_submissao=data_limit_submissao,
        )

        if status != "disabled":
            print(f"💾 MongoDB: {status}")

        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        print("\n" + "-" * 60 + "\n")

        if i < len(links):
            time.sleep(SLEEP_NEW_PROCESS)
