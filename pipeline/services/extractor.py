import pdfplumber
import requests
from io import BytesIO


def extract_text_from_pdf_url(url_pdf: str, max_pages=1) -> str:
    """
    Baixa um PDF via URL e extrai texto das primeiras páginas.

    Observações:
      - Não salva o PDF em disco: tudo é processado em memória (BytesIO).
      - Extração é feita com pdfplumber (depende do PDF conter texto selecionável;
        PDFs “escaneados” podem retornar vazio).

    Args:
        url_pdf: URL direta para o PDF.
        max_paginas: máximo de páginas para extrair (default: 1).

    Returns:
        Texto extraído (string). Retorna "" em caso de falha no download.
    """

    # Download do PDF.
    resp = requests.get(url_pdf, headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code != 200:
        print(f"Erro ao baixar {url_pdf}")
        return ""

    texto = ""

    # Abre o PDF a partir do conteúdo em memória.
    with pdfplumber.open(BytesIO(resp.content)) as pdf:
        # Itera páginas e interrompe ao atingir max_paginas.
        for i, pagina in enumerate(pdf.pages):
            if i >= max_pages:
                break
            # extract_text() pode retornar None dependendo do conteúdo da página.
            texto += (pagina.extract_text() or "") + "\n"

    return texto.strip()