import requests
from bs4 import BeautifulSoup


def coletar_links_pdfs_facepe(url_lista: str) -> list[str]:
    """
    Abre a página de listagem de editais da FACEPE e coleta links diretos de PDFs.

    Estratégia:
      - Faz GET na URL de listagem (HTML).
      - Procura botões oficiais de download (<a class="avia-button">).
      - Dentro de cada botão, valida se existe um <span ...> com texto "Download".
      - Mantém apenas hrefs que terminem com ".pdf".
      - Deduplica links mantendo a ordem de descoberta.

    Retorno:
      - Lista de URLs (strings) apontando diretamente para PDFs.
    """
    resp = requests.get(
        url_lista,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )
    # Levanta exceção para erros HTTP (4xx/5xx).
    resp.raise_for_status()

    # Parse do HTML usando o parser lxml (rápido e robusto).
    soup = BeautifulSoup(resp.text, "lxml")

    links = []
    vistos = set()

    # Pega apenas botões oficiais de download (dependente da estrutura do site).
    botoes = soup.find_all("a", class_="avia-button")

    for a in botoes:
        href = a.get("href")
        if not href:
            continue

        # Verifica se dentro do botão existe o span com texto "Download"
        # (evita pegar botões que não são downloads).
        span = a.find("span", class_="avia_iconbox_title")
        if not span:
            continue

        if span.get_text(strip=True).lower() != "download":
            continue

        # Garante que é PDF real (link direto).
        if not href.lower().endswith(".pdf"):
            continue

        # Remove fragmentos tipo #... para evitar duplicações artificiais.
        href = href.split("#", 1)[0].strip()

        # Deduplica preservando ordem.
        if href not in vistos:
            vistos.add(href)
            links.append(href)

    return links
