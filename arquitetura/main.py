import os
import json

from services.scraper import coletar_links_pdfs_facepe
from services.extractor import extrair_texto_pdf_url
from services.analyzer import analisar_texto


URL_FACEPE = "https://www.facepe.br/editais/todos/?c=aberto"

PASTA_TEXTOS = "data/textos_brutos"
PASTA_RESULTADOS = "data/resultados_json"

os.makedirs(PASTA_TEXTOS, exist_ok=True)
os.makedirs(PASTA_RESULTADOS, exist_ok=True)


def etapa_scraping():
    links = coletar_links_pdfs_facepe(URL_FACEPE)
    print(f"{len(links)} PDFs encontrados.")
    return links


def etapa_extracao(links):
    for link in links:
        extrair_texto_pdf_url(link, PASTA_TEXTOS)


def etapa_analise():
    arquivos = os.listdir(PASTA_TEXTOS)

    for arquivo in arquivos:

        caminho = os.path.join(PASTA_TEXTOS, arquivo)

        with open(caminho, "r", encoding="utf-8") as f:
            texto = f.read()

        url_pdf = arquivo.replace(".txt", ".pdf")

        print(f"Analisando: {arquivo}")

        resultado = analisar_texto(texto, url_pdf)

        caminho_saida = os.path.join(PASTA_RESULTADOS, arquivo.replace(".txt", ".json"))

        with open(caminho_saida, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)

        print(f"JSON salvo: {arquivo.replace('.txt', '.json')}")


if __name__ == "__main__":

    print("\n1 - Scraping")
    print("2 - Extrair textos")
    print("3 - Analisar textos")
    print("4 - Rodar tudo\n")

    opcao = input("Escolha a etapa: ")

    if opcao == "1":
        etapa_scraping()

    elif opcao == "2":
        links = etapa_scraping()
        etapa_extracao(links)

    elif opcao == "3":
        etapa_analise()

    elif opcao == "4":
        links = etapa_scraping()
        etapa_extracao(links)
        etapa_analise()
        

        
        
    

