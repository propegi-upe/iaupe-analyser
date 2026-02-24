import os
import json
import re
from io import BytesIO
from urllib.parse import urljoin

import pdfplumber
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# Token de acesso (Router API).
HF_TOKEN = os.getenv("HF_TOKEN")


def coletar_links_pdfs_facepe(url_lista: str, timeout: int = 30, limit: int | None = None) -> list[str]:
    """
    Coleta links diretos de PDFs a partir da página de editais (HTML) da FACEPE.

    Args:
        url_lista (str): URL da listagem (ex: "https://www.facepe.br/editais/todos/?c=aberto")
        timeout (int): timeout HTTP
        limit (int|None): limitar quantidade de PDFs retornados (None = todos)

    Returns:
        list[str]: lista de URLs absolutas para PDFs
    """
    resp = requests.get(url_lista, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code != 200:
        raise RuntimeError(f"Erro ao abrir página de editais: {resp.status_code}")

    # Diagnóstico: garante que parseamos HTML (ajuda quando a URL não é a esperada)
    content_type = resp.headers.get("Content-Type", "")
    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
        raise RuntimeError(f"Conteúdo inesperado (não parece HTML). Content-Type={content_type}")

    soup = BeautifulSoup(resp.text, "lxml")

    links: list[str] = []
    vistos: set[str] = set()

    # Coleta todos os <a> com href que contenha ".pdf"
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if ".pdf" not in href.lower():
            continue

        url_pdf = urljoin(url_lista, href)  # transforma em URL absoluta (caso seja relativa)
        if url_pdf not in vistos:
            vistos.add(url_pdf)
            links.append(url_pdf)

        if limit is not None and len(links) >= limit:
            break

    return links


def extrair_texto_pdf_url(url_pdf: str, max_paginas: int = 5, timeout: int = 30) -> str:
    """
    Faz download de um PDF via URL e extrai texto das primeiras páginas.

    Args:
        url_pdf (str): URL direta do PDF
        max_paginas (int): número máximo de páginas a ler
        timeout (int): timeout do download

    Returns:
        str: texto extraído
    """
    response = requests.get(url_pdf, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})

    if response.status_code != 200:
        raise RuntimeError(f"Erro ao baixar PDF: {response.status_code}")

    # Diagnóstico opcional: valida Content-Type (pode vir HTML por redirecionamento/bloqueio)
    content_type = response.headers.get("Content-Type", "")
    if "application/pdf" not in content_type.lower():
        # Não é obrigatório, mas evita você tentar abrir HTML como PDF (que gera o erro do /Root)
        # Se o servidor não enviar content-type certinho, você pode comentar esse bloco.
        raise RuntimeError(f"Conteúdo baixado não parece PDF. Content-Type={content_type}")

    texto = ""
    with pdfplumber.open(BytesIO(response.content)) as pdf:
        for i, pagina in enumerate(pdf.pages):
            if i >= max_paginas:
                break
            texto += (pagina.extract_text() or "") + "\n"

    return texto.strip()


def analisar_publico_alvo(texto_edital: str) -> dict:
    """
    Envia o texto do edital para um LLM (via Hugging Face Router) pedindo um JSON estruturado.

    Estratégia:
      - Monta um prompt com regras bem explícitas
      - Chama o endpoint /v1/chat/completions
      - Tenta fazer json.loads do retorno
      - Se o modelo "vazar" texto extra, tenta extrair o primeiro bloco { ... } via regex
      - Se falhar, retorna estrutura vazia + campo raw com o conteúdo original
    """
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN não encontrado no .env")

    url = "https://router.huggingface.co/v1/chat/completions"

    prompt = f"""
Você é um analista de editais de fomento.

Tarefa:
A partir do texto do edital, retorne APENAS um JSON válido exatamente neste formato:

{{
  "publico_alvo": "Quem é o público-alvo principal do edital (frase curta).",
  "descricao": "Resumo curto do edital (2 a 4 frases).",
  "criterios_publico_alvo": ["Somente critérios/requisitos de elegibilidade do público-alvo (beneficiários/bolsistas)."],
  "criterios_proponente": ["Somente critérios/requisitos para o proponente e/ou instituição que submete a proposta."],
  "observacoes": ["Observações úteis (ex: datas, duração, restrições relevantes)."]
}}

Regras obrigatórias:
- Responda SOMENTE com JSON. Sem texto fora do JSON.
- Não invente: se algo não estiver claro no edital, use "" ou [].
- Seja fiel ao texto: não extrapole.
- Escreva em português.
- "criterios_publico_alvo" NÃO pode conter regras do proponente/instituição.
- "criterios_proponente" NÃO pode conter regras do público-alvo.

Texto do edital:
{texto_edital}
""".strip()

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }

    body = {
        "model": "mistralai/Mistral-7B-Instruct-v0.2",
        "messages": [
            {"role": "system", "content": "Responda apenas JSON válido no formato solicitado. Sem texto extra."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 900,
    }

    resp = requests.post(url, headers=headers, json=body, timeout=60)

    if not resp.ok:
        raise RuntimeError(f"Hugging Face {resp.status_code}: {resp.text}")

    result = resp.json()
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

    # Parse robusto do JSON
    try:
        return json.loads(content)
    except Exception:
        # Extrai o primeiro objeto JSON multilinha (caso venha texto extra)
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass

    return {
        "publico_alvo": "",
        "descricao": "",
        "criterios_publico_alvo": [],
        "criterios_proponente": [],
        "observacoes": [],
        "raw": content,
    }


if __name__ == "__main__":
    print("Token carregado:", bool(HF_TOKEN))

    # 1) Página de listagem de editais abertos (HTML)
    url_lista = "https://www.facepe.br/editais/todos/?c=aberto"

    # 2) Coleta automaticamente links diretos de PDFs na página
    pdf_links = coletar_links_pdfs_facepe(url_lista, limit=1)

    if not pdf_links:
        raise RuntimeError("Nenhum link de PDF encontrado na página de editais.")

    url_pdf = pdf_links[0]
    print("PDF encontrado:", url_pdf)

    # 3) Extrai texto do PDF via URL
    texto = extrair_texto_pdf_url(url_pdf, max_paginas=6)

    # 4) Analisa o público-alvo via LLM
    resultado = analisar_publico_alvo(texto)

    # 5) Imprime JSON final
    print("\nResultado:")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    
    