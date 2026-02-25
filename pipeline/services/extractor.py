import pdfplumber
import requests
from io import BytesIO


def extrair_texto_pdf_url(url_pdf: str, max_paginas=1) -> str:

    resp = requests.get(url_pdf, headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code != 200:
        print(f"Erro ao baixar {url_pdf}")
        return ""

    texto = ""

    with pdfplumber.open(BytesIO(resp.content)) as pdf:
        for i, pagina in enumerate(pdf.pages):
            if i >= max_paginas:
                break
            texto += (pagina.extract_text() or "") + "\n"

    return texto.strip()