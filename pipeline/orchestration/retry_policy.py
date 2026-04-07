import re
import time

from pdf_pipeline.analyzer import analyze_text
from .settings import MAX_RETRIES_GEMINI


def sleep_retry_429(raw: str) -> bool:
    """
    Se a mensagem do Gemini indicar 'Please retry in XXs', aguarda esse tempo e retorna True.
    Caso nao consiga extrair o tempo, retorna False.
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
    Tenta analisar o texto com retry para erros temporarios do Gemini:
    - 429: respeita o tempo sugerido
    - 503: aguarda progressivamente e tenta novamente
    """
    for tentativa in range(1, MAX_RETRIES_GEMINI + 1):
        # tentativa principal de analise
        resultado = analyze_text(texto, link)

        if not resultado.get("erro"):
            return resultado

        raw = (resultado.get("raw") or "").lower()

        if "429" in raw:
            # respeita o tempo sugerido pela API quando houver rate limit
            if tentativa < MAX_RETRIES_GEMINI and sleep_retry_429(raw):
                continue
            return resultado

        if "503" in raw:
            # indisponibilidade temporaria: aplica backoff progressivo
            if tentativa < MAX_RETRIES_GEMINI:
                espera = 30 * tentativa
                print(
                    f"⏳ Gemini 503: aguardando {espera}s antes da tentativa {tentativa + 1}/{MAX_RETRIES_GEMINI}..."
                )
                time.sleep(espera)
                continue
            return resultado

        return resultado

    # fallback defensivo caso o loop termine de forma inesperada
    return {"erro": "Falha inesperada no retry do Gemini", "raw": ""}
