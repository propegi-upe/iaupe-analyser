import json
import os

from services.scraper import coletar_links_pdfs_facepe
from services.extractor import extrair_texto_pdf_url
from services.analyzer import analisar_texto

URL_FACEPE = "https://www.facepe.br/editais/todos/?c=aberto"

_raw_limit = (os.getenv("PIPELINE_LIMIT") or "all").strip().lower()
LIMIT = None if _raw_limit in ("all", "0", "none", "") else int(_raw_limit)


def executar_pipeline():
    links = coletar_links_pdfs_facepe(URL_FACEPE)
    if not links:
        print("Nenhum PDF encontrado.")
        return

    links = links if LIMIT is None else links[:LIMIT]
    print(f"{len(links)} PDFs para processar.\n")

    for link in links:
        print(f"📄 {link}")
        texto = extrair_texto_pdf_url(link)
        if not texto:
            print("Texto vazio.\n")
            continue

        resultado = analisar_texto(texto, link)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        print("\n" + "-" * 60 + "\n")


if __name__ == "__main__":
    executar_pipeline()



