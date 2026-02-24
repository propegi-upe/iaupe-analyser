import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def coletar_links_pdfs_facepe(url_lista: str) -> list[str]:
    resp = requests.get(url_lista, headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code != 200:
        raise RuntimeError("Erro ao acessar página FACEPE")

    soup = BeautifulSoup(resp.text, "lxml")

    links = []
    vistos = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower():
            url_pdf = urljoin(url_lista, href)
            if url_pdf not in vistos:
                vistos.add(url_pdf)
                links.append(url_pdf)

    return links