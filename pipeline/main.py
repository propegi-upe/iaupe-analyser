import json
import os
import re
import time

from services.scraper import coletar_links_pdfs_facepe
from services.extractor import extrair_texto_pdf_url
from services.analyzer import analisar_texto
from services.db_mongo import ja_existe, salvar

URL_FACEPE = "https://www.facepe.br/editais/todos/?c=aberto"

_raw_limit = (os.getenv("PIPELINE_LIMIT") or "all").strip().lower()
LIMIT = None if _raw_limit in ("all", "0", "none", "") else int(_raw_limit)


def _sleep_retry_429(raw: str) -> bool:
    """
    Se a mensagem do Gemini indicar 'Please retry in XXs', aguarda esse tempo e retorna True.
    Caso não consiga extrair o tempo, retorna False.
    """
    m = re.search(r"retry in ([0-9]+(\.[0-9]+)?)s", (raw or "").lower())
    if not m:
        return False

    secs = int(float(m.group(1))) + 2  # margem
    print(f"⏳ Gemini 429: aguardando {secs}s e tentando novamente...")
    time.sleep(secs)
    return True


def executar_pipeline():
    links = coletar_links_pdfs_facepe(URL_FACEPE)
    if not links:
        print("Nenhum PDF encontrado.")
        return

    links = links if LIMIT is None else links[:LIMIT]
    print(f"{len(links)} PDFs para processar.\n")

    for i, link in enumerate(links, start=1):
        if ja_existe(link):
            print(f"[{i}/{len(links)}] ✅ Já salvo no MongoDB (status=ok): {link}")
            i < len(links) and time.sleep(60)
            continue

        print(f"[{i}/{len(links)}] 📄 {link}")
        texto = extrair_texto_pdf_url(link)

        if not texto:
            print("Texto vazio.\n")
            status = salvar(link, {"erro": "Texto vazio"}, texto_preview="")
            print(f"💾 MongoDB: {status}")
            i < len(links) and time.sleep(60)
            continue

        resultado = analisar_texto(texto, link)

        # Retry 1x quando for quota/rate limit (429) com tempo sugerido pela API
        if resultado.get("erro") and "429" in (resultado.get("raw") or ""):
            if _sleep_retry_429(resultado.get("raw") or ""):
                resultado = analisar_texto(texto, link)

        status = salvar(link, resultado, texto_preview=texto)

        print(f"💾 MongoDB: {status}")
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        print("\n" + "-" * 60 + "\n")

        i < len(links) and time.sleep(60)


if __name__ == "__main__":
    executar_pipeline()