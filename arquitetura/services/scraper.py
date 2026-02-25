import requests
from bs4 import BeautifulSoup


def coletar_links_pdfs_facepe(url_lista: str) -> list[str]:
    resp = requests.get(
        url_lista,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    links = []
    vistos = set()

    # Pega apenas botões oficiais de download
    botoes = soup.find_all("a", class_="avia-button")

    for a in botoes:
        href = a.get("href")
        if not href:
            continue

        # Verifica se dentro do botão existe o span com texto "Download"
        span = a.find("span", class_="avia_iconbox_title")
        if not span:
            continue

        if span.get_text(strip=True).lower() != "download":
            continue

        # Garante que é PDF real
        if not href.lower().endswith(".pdf"):
            continue

        # Remove fragmentos tipo #...
        href = href.split("#", 1)[0].strip()

        if href not in vistos:
            vistos.add(href)
            links.append(href)

    return links


#vamos testar o scraper direto no arquivo mesmo
if __name__ == "__main__":
    url = "https://www.facepe.br/editais/todos/"
    links = coletar_links_pdfs_facepe(url)

    print("\nPDFs encontrados:\n")

    for i, link in enumerate(links, 1):
        print(f"{i:03d} - {link}")

    print(f"\nTotal: {len(links)} PDFs encontrados.")