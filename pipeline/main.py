import json
import os
import re
import time

from services.scraper import collect_facepe_pdf_links
from services.extractor import extract_text_from_pdf_url
from services.analyzer import analyze_text
from services.db_mongo import already_exists, save

URL_FACEPE = "https://www.facepe.br/editais/todos/?c=aberto"

raw_limit = (os.getenv("PIPELINE_LIMIT") or "all").strip().lower()
LIMIT = None if raw_limit in ("all", "0", "none", "") else int(raw_limit)

SLEEP_ALREADY_EXISTS = int((os.getenv("SLEEP_ALREADY_EXISTS") or "5").strip())
SLEEP_NEW_PROCESS = int((os.getenv("SLEEP_NEW_PROCESS") or "60").strip())
SLEEP_EMPTY_TEXT = int((os.getenv("SLEEP_EMPTY_TEXT") or "5").strip())

MAX_RETRIES_GEMINI = int((os.getenv("MAX_RETRIES_GEMINI") or "3").strip())


def sleep_retry_429(raw: str) -> bool:
    """
    Se a mensagem do Gemini indicar 'Please retry in XXs', aguarda esse tempo e retorna True.
    Caso não consiga extrair o tempo, retorna False.
    """
    m = re.search(r"retry in ([0-9]+(\.[0-9]+)?)s", (raw or "").lower())
    if not m:
        return False

    secs = int(float(m.group(1))) + 2
    print(f"⏳ Gemini 429: aguardando {secs}s e tentando novamente...")
    time.sleep(secs)
    return True


def retry_analyze_text(texto: str, link: str) -> dict:
    """
    Tenta analisar o texto com retry para erros temporários do Gemini:
    - 429: respeita o tempo sugerido
    - 503: aguarda progressivamente e tenta novamente
    """
    for tentativa in range(1, MAX_RETRIES_GEMINI + 1):
        resultado = analyze_text(texto, link)

        if not resultado.get("erro"):
            return resultado

        raw = (resultado.get("raw") or "").lower()

        if "429" in raw:
            if tentativa < MAX_RETRIES_GEMINI and sleep_retry_429(raw):
                continue
            return resultado

        if "503" in raw:
            if tentativa < MAX_RETRIES_GEMINI:
                espera = 30 * tentativa
                print(
                    f"⏳ Gemini 503: aguardando {espera}s antes da tentativa {tentativa + 1}/{MAX_RETRIES_GEMINI}..."
                )
                time.sleep(espera)
                continue
            return resultado

        return resultado

    return {"erro": "Falha inesperada no retry do Gemini", "raw": ""}


def run_pipeline():
    links = collect_facepe_pdf_links(URL_FACEPE)
    if not links:
        print("Nenhum PDF encontrado.")
        return

    links = links if LIMIT is None else links[:LIMIT]
    print(f"{len(links)} PDFs para processar.\n")

    for i, link in enumerate(links, start=1):
        if already_exists(link):
            print(f"[{i}/{len(links)}] ✅ Já salvo no MongoDB (status=ok): {link}")
            if i < len(links):
                time.sleep(SLEEP_ALREADY_EXISTS)
            continue

        print(f"[{i}/{len(links)}] 📄 {link}")
        texto = extract_text_from_pdf_url(link)

        if not texto:
            print("Texto vazio.\n")
            status = save(link, {"erro": "Texto vazio"}, texto_preview="")
            if status != "disabled":
                print(f"💾 MongoDB: {status}")
            if i < len(links):
                time.sleep(SLEEP_EMPTY_TEXT)
            continue

        resultado = retry_analyze_text(texto, link)

        status = save(link, resultado, texto_preview=texto)

        if status != "disabled":
            print(f"💾 MongoDB: {status}")

        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        print("\n" + "-" * 60 + "\n")

        if i < len(links):
            time.sleep(SLEEP_NEW_PROCESS)


if __name__ == "__main__":
    run_pipeline()