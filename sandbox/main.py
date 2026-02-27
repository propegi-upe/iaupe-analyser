import os
import json
import re
from io import BytesIO
from urllib.parse import urljoin
from typing import Optional
import pdfplumber
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai

load_dotenv(override=True)
API_KEY = (os.getenv("GEMINI_API_KEY") or os.getenv("GAMINI_API_KEY") or "").strip()
MODEL = "gemini-2.5-flash"


def coletar_links_pdfs_facepe(url_lista: str, timeout: int = 30, limit: Optional[int] = None) -> list[str]:
    resp = requests.get(url_lista, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    links: list[str] = []
    vistos: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if ".pdf" not in href.lower():
            continue
        url_pdf = urljoin(url_lista, href)
        if url_pdf in vistos:
            continue
        vistos.add(url_pdf)
        links.append(url_pdf)
        if limit is not None and len(links) >= limit:
            break

    return links


def extrair_texto_pdf_url(url_pdf: str, max_paginas: int = 5, timeout: int = 30) -> str:
    response = requests.get(url_pdf, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()

    texto = ""
    with pdfplumber.open(BytesIO(response.content)) as pdf:
        for i, pagina in enumerate(pdf.pages):
            if i >= max_paginas:
                break
            texto += (pagina.extract_text() or "") + "\n"
    return texto.strip()


def analisar_publico_alvo(texto_edital: str) -> dict:
    if not API_KEY:
        raise RuntimeError("Defina GEMINI_API_KEY no .env")

    client = genai.Client(api_key=API_KEY)

    prompt = f"""
Retorne APENAS um JSON válido no formato:

{{
  "publico_alvo": "",
  "descricao": "",
  "criterios_publico_alvo": [],
  "criterios_proponente": [],
  "observacoes": []
}}

Texto do edital:
{texto_edital}
""".strip()

    try:
        resp = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
    except TypeError:
        resp = client.models.generate_content(model=MODEL, contents=prompt)

    content = (getattr(resp, "text", None) or "").strip()

    try:
        return json.loads(content)
    except Exception:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        return {"erro": "JSON inválido", "raw": content}


if __name__ == "__main__":
    print("API key carregada:", bool(API_KEY))

    url_lista = "https://www.facepe.br/editais/todos/?c=aberto"
    pdf_links = coletar_links_pdfs_facepe(url_lista, limit=1)
    if not pdf_links:
        raise RuntimeError("Nenhum link de PDF encontrado.")

    url_pdf = pdf_links[0]
    print("PDF:", url_pdf)

    texto = extrair_texto_pdf_url(url_pdf, max_paginas=6)
    resultado = analisar_publico_alvo(texto)

    print(json.dumps(resultado, ensure_ascii=False, indent=2))

