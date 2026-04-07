import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

SOURCE_KEY = "finep"
SOURCE_LABEL = "FINEP"
BASE_URL = "https://www.finep.gov.br/chamadas-publicas/chamadaspublicas?situacao=aberta"
MONGO_COLLECTION = "editais_finep"


def collect_links(url_lista: str = BASE_URL) -> list[str]:
    """
    Coleta links de PDFs de chamadas abertas da FINEP.

    Fluxo:
    1) coleta paginas de eventos na listagem
    2) entra em cada evento e extrai links PDF da tabela
    """
    resp = requests.get(
        url_lista,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    links: list[str] = []
    vistos: set[str] = set()

    # coleta links de paginas de eventos na listagem atual
    eventos: list[str] = []
    vistos_eventos: set[str] = set()

    for a in soup.select("div.item h3 a[href], h3 a[href]"):
        href_evento = (a.get("href") or "").split("#", 1)[0].strip()
        if not href_evento:
            continue

        url_evento = urljoin(url_lista, href_evento)

        if "/chamadas-publicas/chamadapublica/" not in url_evento.lower():
            continue

        if url_evento not in vistos_eventos:
            vistos_eventos.add(url_evento)
            eventos.append(url_evento)

    # entra em cada evento e coleta documentos PDF
    for url_evento in eventos:
        try:
            resp_evento = requests.get(
                url_evento,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30,
            )
            resp_evento.raise_for_status()
        except requests.RequestException:
            continue

        soup_evento = BeautifulSoup(resp_evento.text, "lxml")

        for a_doc in soup_evento.select("table a[href]"):
            href_doc = (a_doc.get("href") or "").split("#", 1)[0].strip()
            if not href_doc:
                continue

            url_doc = urljoin(url_evento, href_doc)

            if ".pdf" not in url_doc.lower():
                continue

            if url_doc not in vistos:
                vistos.add(url_doc)
                links.append(url_doc)

    return links