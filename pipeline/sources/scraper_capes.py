import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

SOURCE_KEY = "capes"
SOURCE_LABEL = "CAPES"
BASE_URL = "https://www.gov.br/capes/pt-br/assuntos/editais-e-resultados-capes"
MONGO_COLLECTION = "editais_capes"


def clean_href(href: str) -> str:
    # normaliza href:
    # - remove fragmentos (#...) para evitar urls duplicadas
    # - remove espacos
    href = (href or "").split("#", 1)[0].strip()
    # corrige caso raro de url terminando com .pdf/ (barra extra no final)
    if href.endswith("/") and href.lower().endswith(".pdf/"):
        href = href[:-1]
    return href


def is_pdf_url(url: str) -> bool:
    # verifica se a url parece ser pdf
    # - .pdf no final
    # - ou .pdf com querystring (ex: .pdf?download=1)
    u = (url or "").lower()
    return u.endswith(".pdf") or ".pdf?" in u


def find_heading(soup: BeautifulSoup, title: str):
    # procura um heading (h2/h3/h4) com o texto exato desejado
    # isso ajuda a ancorar a raspagem em secoes do site sem depender de css fixo
    wanted = title.strip().lower()
    return soup.find(
        lambda tag: tag.name in ("h2", "h3", "h4")
        and tag.get_text(" ", strip=True).strip().lower() == wanted
    )


def collect_open_call_pages(index_url: str, soup: BeautifulSoup) -> list[str]:
    # a pagina indice da capes costuma ter uma secao chamada "editais abertos"
    # aqui coletamos as subpaginas (programas/areas) listadas nessa secao
    heading = find_heading(soup, "Editais Abertos")
    if not heading:
        return []

    # pega o primeiro container de lista (ul/ol) depois do titulo
    container = heading.find_next(["ul", "ol"])
    if not container:
        return []

    pages: list[str] = []
    vistos: set[str] = set()

    # itera somente li diretos para evitar capturar listas aninhadas
    for li in container.find_all("li", recursive=False):
        # tenta pegar link com classe external-link; senao pega o primeiro link disponivel
        a = li.find("a", class_="external-link", href=True) or li.find("a", href=True)
        if not a:
            continue

        href = clean_href(a.get("href") or "")
        if not href:
            continue

        # resolve href relativo em url absoluta
        full = urljoin(index_url, href)
        parsed = urlparse(full)

        # filtra para manter somente links do dominio gov.br e caminho relacionado a capes
        if (parsed.netloc or "").lower() != "www.gov.br":
            continue
        if "/capes/" not in (parsed.path or ""):
            continue

        if full not in vistos:
            vistos.add(full)
            pages.append(full)

    return pages


def collect_pdf_links_from_program_page(page_url: str, soup: BeautifulSoup) -> list[str]:
    # em cada subpagina, os documentos geralmente ficam em tabela
    # aqui coleto apenas os links que apontam para pdf
    links: list[str] = []
    vistos: set[str] = set()

    # tentativa 1: achar a tabela "listing" apos o heading "editais"
    heading = find_heading(soup, "Editais")
    table = None

    if heading is not None:
        table = heading.find_next(
            lambda tag: tag.name == "table" and "listing" in (tag.get("class", []) or [])
        )

    # tentativa 2 (fallback): procurar seletores comuns no site
    if table is None:
        table = soup.select_one("table.arquivos.listing") or soup.select_one("table.listing")

    # se nao achou tabela, nao ha pdfs (ou o layout mudou)
    if table is None:
        return []

    # percorre todos os links dentro da tabela
    for a in table.select("a[href]"):
        href = clean_href(a.get("href") or "")
        if not href:
            continue

        # resolve para url absoluta e normaliza
        full = urljoin(page_url, href)
        full = clean_href(full)

        # filtra para manter somente pdf
        if not is_pdf_url(full):
            continue

        if full not in vistos:
            vistos.add(full)
            links.append(full)

    return links


def collect_links(url_lista: str = BASE_URL) -> list[str]:
    """
    Coleta links de PDFs de editais da CAPES.

    Se receber a pagina indice, navega para subpaginas de "Editais Abertos".
    Se receber pagina de programa, extrai PDFs diretamente dela.
    """
    # funcao principal do scraper (entrypoint do pipeline)
    # retorna uma lista de urls de pdf para o pipeline processar
    headers = {"User-Agent": "Mozilla/5.0"}

    # baixa a pagina inicial (ou a pagina informada) e faz parse do html
    try:
        resp = requests.get(url_lista, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"Erro ao acessar CAPES: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")

    # se a url for a pagina indice, coletamos as subpaginas em "editais abertos"
    # se nao for indice, tratamos a url como pagina final de programa
    is_index = "/editais-e-resultados-capes" in (urlparse(url_lista).path or "")
    program_pages = collect_open_call_pages(url_lista, soup) if is_index else [url_lista]

    all_pdfs: list[str] = []
    vistos: set[str] = set()

    for page_url in program_pages:
        # entra em cada subpagina e extrai os pdfs
        try:
            r = requests.get(page_url, headers=headers, timeout=30)
            r.raise_for_status()
        except requests.RequestException:
            # falha em uma subpagina nao derruba o processo; segue a proxima
            continue

        page_soup = BeautifulSoup(r.text, "lxml")
        pdfs = collect_pdf_links_from_program_page(page_url, page_soup)

        # agrega mantendo ordem e removendo duplicidade
        for pdf in pdfs:
            if pdf not in vistos:
                vistos.add(pdf)
                all_pdfs.append(pdf)

    return all_pdfs