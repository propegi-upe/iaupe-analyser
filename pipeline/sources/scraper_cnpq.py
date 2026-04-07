import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

SOURCE_KEY = "cnpq"
SOURCE_LABEL = "CNPq"
BASE_URL = "http://memoria2.cnpq.br/web/guest/chamadas-publicas"
MONGO_COLLECTION = "editais_cnpq"


def collect_links(url_lista: str = BASE_URL) -> list[str]:
    """Coleta links de chamadas publicas a partir da pagina do CNPq."""
    try:
        resp = requests.get(
            url_lista,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"Erro ao acessar CNPq: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")

    links: list[str] = []
    vistos: set[str] = set()

    # seletor principal da estrutura atual do site
    anchors = soup.select("div.links-normas.pull-left a.btn[href]")

    # fallback defensivo caso o HTML mude levemente
    if not anchors:
        anchors = soup.select("a.btn[href]")

    for a in anchors:
        href = (a.get("href") or "").split("#", 1)[0].strip()
        if not href:
            continue

        full_href = urljoin(url_lista, href)
        host = (urlparse(full_href).netloc or "").lower()

        # evita links que nao sao paginas de resultado/chamada
        if "resultado.cnpq.br" not in host and "efomento.cnpq.br" not in host:
            continue

        if full_href not in vistos:
            vistos.add(full_href)
            links.append(full_href)

    return links