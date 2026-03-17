import os
from dotenv import load_dotenv
from google import genai

load_dotenv(override=True)

api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GAMINI_API_KEY") or "").strip()
if not api_key:
    raise RuntimeError("Defina GEMINI_API_KEY no .env ou no ambiente")

client = genai.Client(api_key=api_key)

def run(model: str):
    r = client.models.generate_content(model=model, contents="Explique IA em poucas palavras.")
    print(r.text)

try:
    run("gemini-2.5-flash")
except Exception as e:
    msg = str(e)
    if "API_KEY_INVALID" in msg or "API key not valid" in msg:
        raise SystemExit("API key inválida. Gere outra no Google AI Studio e atualize o .env.\n\n" + msg)
    if "models/" in msg and "not found" in msg.lower():
        run("gemini-flash-latest")
    else:
        raise