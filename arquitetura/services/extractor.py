import pdfplumber
import requests
from io import BytesIO
import os


def extrair_texto_pdf_url(url_pdf: str, pasta_destino: str, max_paginas=3):

    resp = requests.get(url_pdf, headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code != 200:
        print(f"Erro ao baixar {url_pdf}")
        return

    texto = ""

    with pdfplumber.open(BytesIO(resp.content)) as pdf:
        for i, pagina in enumerate(pdf.pages):
            if i >= max_paginas:
                break
            texto += (pagina.extract_text() or "") + "\n"

    nome_arquivo = url_pdf.split("/")[-1].replace(".pdf", ".txt")
    caminho = os.path.join(pasta_destino, nome_arquivo)

    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto.strip())

    print(f"Texto salvo: {nome_arquivo}")