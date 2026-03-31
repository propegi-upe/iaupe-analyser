import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

SOURCE_KEY = "capes"
SOURCE_LABEL = "CAPES"

BASE_URL = "https://www.gov.br/capes/pt-br/assuntos/editais-e-resultados-capes"
MONGO_COLLECTION = "editais_capes"


def clean_href(href: str) -> str:
    href = (href or "").split("#", 1)[0].strip()
    if href.endswith("/") and href.lower().endswith(".pdf/"):
        href = href[:-1]
    return href


def is_pdf_url(url: str) -> bool:
    u = (url or "").lower()
    return u.endswith(".pdf") or ".pdf?" in u


def find_heading(soup: BeautifulSoup, title: str):
    wanted = title.strip().lower()
    return soup.find(
        lambda tag: tag.name in ("h2", "h3", "h4")
        and tag.get_text(" ", strip=True).strip().lower() == wanted
    )


def collect_open_call_pages(index_url: str, soup: BeautifulSoup) -> list[str]:
    heading = find_heading(soup, "Editais Abertos")
    if not heading:
        return []

    container = heading.find_next(["ul", "ol"])
    if not container:
        return []

    pages: list[str] = []
    vistos: set[str] = set()

    for li in container.find_all("li", recursive=False):
        a = li.find("a", class_="external-link", href=True) or li.find("a", href=True)
        if not a:
            continue

        href = clean_href(a.get("href") or "")
        if not href:
            continue

        full = urljoin(index_url, href)
        parsed = urlparse(full)
        if (parsed.netloc or "").lower() != "www.gov.br":
            continue
        if "/capes/" not in (parsed.path or ""):
            continue

        if full not in vistos:
            vistos.add(full)
            pages.append(full)

    return pages


def collect_pdf_links_from_program_page(page_url: str, soup: BeautifulSoup) -> list[str]:
    links: list[str] = []
    vistos: set[str] = set()

    heading = find_heading(soup, "Editais")
    table = None

    if heading is not None:
        table = heading.find_next(
            lambda tag: tag.name == "table" and "listing" in (tag.get("class", []) or [])
        )

    if table is None:
        table = soup.select_one("table.arquivos.listing") or soup.select_one("table.listing")

    if table is None:
        return []

    for a in table.select("a[href]"):
        href = clean_href(a.get("href") or "")
        if not href:
            continue

        full = urljoin(page_url, href)
        full = clean_href(full)
        if not is_pdf_url(full):
            continue

        if full not in vistos:
            vistos.add(full)
            links.append(full)

    return links


def collect_links(url_lista: str = BASE_URL) -> list[str]:
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(url_lista, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"Erro ao acessar CAPES: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")

    is_index = "/editais-e-resultados-capes" in (urlparse(url_lista).path or "")
    program_pages = collect_open_call_pages(url_lista, soup) if is_index else [url_lista]

    all_pdfs: list[str] = []
    vistos: set[str] = set()

    for page_url in program_pages:
        try:
            r = requests.get(page_url, headers=headers, timeout=30)
            r.raise_for_status()
        except requests.RequestException:
            continue

        page_soup = BeautifulSoup(r.text, "lxml")
        pdfs = collect_pdf_links_from_program_page(page_url, page_soup)

        for pdf in pdfs:
            if pdf not in vistos:
                vistos.add(pdf)
                all_pdfs.append(pdf)

    return all_pdfs