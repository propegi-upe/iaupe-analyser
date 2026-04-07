import requests
from bs4 import BeautifulSoup

SOURCE_KEY = "facepe"
SOURCE_LABEL = "FACEPE"
BASE_URL = "https://www.facepe.br/editais/todos/?c=aberto"
MONGO_COLLECTION = "editais_facepe"


def collect_links(url_lista: str = BASE_URL) -> list[str]:
    """
    Coleta links diretos de PDFs da listagem de editais da FACEPE.
    """
    # baixa pagina de listagem de editais abertos
    resp = requests.get(
        url_lista,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    links: list[str] = []
    vistos: set[str] = set()

    # no layout atual, links de download aparecem em botoes "avia-button"
    botoes = soup.find_all("a", class_="avia-button")

    for anchor in botoes:
        href = anchor.get("href")
        if not href:
            continue

        span = anchor.find("span", class_="avia_iconbox_title")
        if not span:
            continue

        # garante que estamos pegando o botao de download do documento
        if span.get_text(strip=True).lower() != "download":
            continue

        if not href.lower().endswith(".pdf"):
            continue

        href = href.split("#", 1)[0].strip()

        if href and href not in vistos:
            vistos.add(href)
            links.append(href)

    return links
