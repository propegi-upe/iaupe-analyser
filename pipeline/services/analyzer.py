import os
import json
import requests
import re
from dotenv import load_dotenv

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")


def analisar_texto(texto: str, url_pdf: str):

    url = "https://router.huggingface.co/v1/chat/completions"

    prompt = f"""
Você é um analista de editais.

Retorne JSON no formato:

{{
  "url_pdf": "",
  "publico_alvo": "",
  "descricao": "",
  "criterios_publico_alvo": [],
  "criterios_proponente": [],
  "observacoes": []
}}

Responda apenas JSON válido.

Edital:
{texto}
""".strip()

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }

    body = {
        "model": "mistralai/Mistral-7B-Instruct-v0.2",
        "messages": [
            {"role": "system", "content": "Responda apenas JSON válido."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 1200,
    }

    resp = requests.post(url, headers=headers, json=body)

    if not resp.ok:
        return {"erro": resp.text}

    result = resp.json()
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

    try:
        return json.loads(content)
    except:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except:
                pass

    return {"erro": "JSON inválido", "raw": content}

