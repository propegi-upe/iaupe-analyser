import json

from services.scraper import coletar_links_pdfs_facepe
from services.extractor import extrair_texto_pdf_url
from services.analyzer import analisar_texto


URL_FACEPE = "https://www.facepe.br/editais/todos/?c=aberto"
LIMIT = 1  # ← Altere aqui se quiser processar mais


def executar_pipeline():

    links = coletar_links_pdfs_facepe(URL_FACEPE)

    if not links:
        print("Nenhum PDF encontrado.")
        return

    print(f"{len(links)} PDFs encontrados.")
    print(f"Processando apenas os primeiros {LIMIT}.\n")

    for link in links[:LIMIT]:

        print(f"📄 Processando: {link}")

        texto = extrair_texto_pdf_url(link)

        if not texto:
            print("Texto vazio.\n")
            continue

        resultado = analisar_texto(texto, link)

        print("Resultado:\n")
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        print("\n" + "-" * 60 + "\n")


if __name__ == "__main__":
    executar_pipeline()
        
    

