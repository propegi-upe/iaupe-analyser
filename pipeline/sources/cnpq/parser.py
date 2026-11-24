from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .constants import INSCRIPTION_REGEX
from .models import CnpqCall
from .url_utils import is_pdf_url, normalize_url


def parse_ptbr_date(value: str) -> datetime | None:
    """Converte datas dd/mm/YYYY para datetime."""
    try:
        return datetime.strptime(value, "%d/%m/%Y")
    except ValueError:
        return None


def extract_inscription_start_date(item) -> datetime | None:
    """
    Extrai a data inicial de inscricao de um card de chamada do CNPq.

    No portal gov.br o card traz o texto "Inscrições: dd/mm/aaaa a dd/mm/aaaa".
    """
    match = INSCRIPTION_REGEX.search(item.get_text(" ", strip=True))
    if not match:
        return None

    return parse_ptbr_date(match.group(1))


def extract_permanent_link(item, page_url: str) -> str:
    """Extrai o link da pagina de detalhe da chamada a partir do card do CNPq."""
    anchor = item.select_one("h2.headline a.summary.url[href]")
    if anchor is None:
        return ""

    href = str(anchor.get("href") or "").strip()
    return normalize_url(urljoin(page_url, href)) if href else ""


def parse_open_calls(html: str, page_url: str) -> list[CnpqCall]:
    """Transforma a pagina "Abertas para Submissao" em chamadas ordenaveis."""
    soup = BeautifulSoup(html, "lxml")
    calls: list[CnpqCall] = []
    seen: set[str] = set()

    for position, item in enumerate(soup.select("div.item")):
        detail_url = extract_permanent_link(item, page_url)
        if not detail_url or detail_url in seen:
            continue

        seen.add(detail_url)
        calls.append(
            CnpqCall(
                detail_url=detail_url,
                position=position,
                inscription_start_date=extract_inscription_start_date(item),
            )
        )

    return calls


def extract_pdf_links_from_detail(html: str, detail_url: str) -> list[str]:
    """
    Extrai o PDF principal ("Chamada") de uma pagina de detalhe do CNPq.

    A pagina lista tambem Anexos, FAQ e planilhas, que nao interessam: so o link
    cujo texto e "Chamada", dentro do corpo da pagina, e o edital em si. Links
    fora do corpo (rodape, carta de servicos) tambem sao ignorados.
    """
    soup = BeautifulSoup(html, "lxml")
    body = soup.select_one("#parent-fieldname-text")
    if body is None:
        return []

    pdf_links: list[str] = []
    seen: set[str] = set()

    for anchor in body.select("a[href]"):
        if anchor.get_text(" ", strip=True).lower() != "chamada":
            continue

        href = str(anchor.get("href") or "").split("#", 1)[0].strip()
        if not href:
            continue

        full_href = urljoin(detail_url, href)
        if not is_pdf_url(full_href) or full_href in seen:
            continue

        seen.add(full_href)
        pdf_links.append(full_href)

    return pdf_links
