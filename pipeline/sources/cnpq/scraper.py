from datetime import datetime

import requests

from .client import fetch_html, fetch_html_or_empty
from .constants import BASE_URL
from .parser import extract_pdf_links_from_detail, parse_open_calls


def sort_open_call_urls(html: str, page_url: str) -> list[str]:
    """
    No CNPq, o critério é a data inicial de inscrição. A fonte prioriza chamadas que têm essa data e coloca as mais recentes primeiro
    Ordena chamadas abertas pela data inicial de inscricao mais recente."""
    calls = parse_open_calls(html, page_url)
    calls.sort(
        key=lambda call: (
            call.inscription_start_date is not None,
            call.inscription_start_date,
            -call.position,
        ),
        reverse=True,
    )
    return [call.detail_url for call in calls]


def collect_links(url_lista: str = BASE_URL) -> list[str]:
    """Coleta links de chamadas publicas abertas a partir da pagina do CNPq."""
    try:
        html = fetch_html(url_lista)
    except requests.RequestException as exc:
        print(f"Erro ao acessar CNPq: {exc}")
        return []

    links: list[str] = []
    seen_links: set[str] = set()
    detail_pages: list[str] = sort_open_call_urls(html, url_lista)

    for detail_url in detail_pages:
        detail_html = fetch_html_or_empty(detail_url)
        for pdf_link in extract_pdf_links_from_detail(detail_html, detail_url):
            if pdf_link not in seen_links:
                seen_links.add(pdf_link)
                links.append(pdf_link)

    if not links and detail_pages:
        return detail_pages

    return links


def collect_calls(url_lista: str = BASE_URL) -> list[tuple[str, datetime | None]]:
    """
    Coleta as chamadas abertas do CNPq como pares (url_pdf, data_publicacao).

    O CNPq NAO publica data de publicacao da chamada - o que existe e a data de
    inicio de inscricao, e ela fica em outra pagina (o card do indice), sem
    ligacao direta com cada PDF extraido das paginas de detalhe. Entao a data
    aqui e sempre None e o front cai no `created_at` para ordenar as chamadas do
    CNPq.
    """
    return [(url, None) for url in collect_links(url_lista)]
