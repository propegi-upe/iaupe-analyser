import os
import json
import re
from dotenv import load_dotenv
from google import genai

# Modelo já confirmado no seu ambiente
MODEL = "gemini-2.5-flash"


def _get_api_key() -> str | None:
    load_dotenv(override=True)
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GAMINI_API_KEY") or "").strip() or None


def _call_gemini(client: genai.Client, model: str, prompt: str) -> str:
    # Tenta forçar JSON quando suportado; se não, cai pro modo normal
    try:
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
    except TypeError:
        resp = client.models.generate_content(model=model, contents=prompt)
    return (getattr(resp, "text", None) or "").strip()


def analyze_text(text: str, pdf_url: str):
    api_key = _get_api_key()
    if not api_key:
        return {"erro": "Defina GEMINI_API_KEY no .env ou no ambiente"}

    client = genai.Client(api_key=api_key)

    prompt = f"""
Você é um analista de editais.

Responda SOMENTE com JSON válido no formato:

{{
  "url_pdf": "{pdf_url}",
  "publico_alvo": "",
  "descricao": "",
  "criterios_publico_alvo": [],
  "criterios_proponente": [],
  "observacoes": []
}}

Edital:
{text}
""".strip()

    try:
        content = _call_gemini(client, MODEL, prompt)
    except Exception as e:
        msg = str(e)
        if "API_KEY_INVALID" in msg or "API key not valid" in msg:
            return {"erro": "API key inválida. Gere uma nova no Google AI Studio e atualize o .env", "raw": msg}
        if "models/" in msg and "not found" in msg.lower():
            # fallback simples e conhecido
            try:
                content = _call_gemini(client, "gemini-flash-latest", prompt)
            except Exception as e2:
                return {"erro": "Modelo Gemini indisponível", "raw": str(e2)}
        else:
            return {"erro": "Falha ao chamar Gemini", "raw": msg}

    try:
        return json.loads(content)
    except Exception:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        return {"erro": "JSON inválido", "raw": content}

