import pdfplumber
import requests
import os
import json
import re
from dotenv import load_dotenv

# Carrega .env
load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

def extrair_texto_pdf(caminho_pdf, max_paginas=5):
    texto = ""
    with pdfplumber.open(caminho_pdf) as pdf:
        for i, pagina in enumerate(pdf.pages):
            if i >= max_paginas:
                break
            texto += (pagina.extract_text() or "") + "\n"
    return texto.strip()


def analisar_publico_alvo(texto_edital):
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN não encontrado no .env")

    url = "https://router.huggingface.co/v1/chat/completions"

    prompt = f"""
Você é um analista de editais de fomento.

Tarefa:
A partir do texto do edital, retorne APENAS um JSON válido exatamente neste formato:

{{
  "publico_alvo": "Quem é o público-alvo principal do edital (frase curta).",
  "descricao": "Resumo curto do edital (2 a 4 frases).",
  "criterios_publico_alvo": ["Somente critérios/requisitos de elegibilidade do público-alvo (beneficiários/bolsistas)."],
  "criterios_proponente": ["Somente critérios/requisitos para o proponente e/ou instituição que submete a proposta."],
  "observacoes": ["Observações úteis (ex: datas, duração, restrições relevantes)."]
}}

Regras obrigatórias:
- Responda SOMENTE com JSON. Sem texto fora do JSON.
- Não invente: se algo não estiver claro no edital, use "" ou [].
- Seja fiel ao texto: não extrapole.
- Escreva em português.
- "criterios_publico_alvo" NÃO pode conter regras do proponente/instituição.
- "criterios_proponente" NÃO pode conter regras do público-alvo.

Texto do edital:
{texto_edital}
""".strip()

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }

    body = {
        "model": "mistralai/Mistral-7B-Instruct-v0.2",
        "messages": [
            {"role": "system", "content": "Responda apenas JSON válido no formato solicitado. Sem texto extra."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 900,
    }

    resp = requests.post(url, headers=headers, json=body, timeout=60)

    if not resp.ok:
        raise RuntimeError(f"Hugging Face {resp.status_code}: {resp.text}")

    result = resp.json()
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

    # Parse robusto
    try:
        return json.loads(content)
    except Exception:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass

    return {
        "publico_alvo": "",
        "descricao": "",
        "criterios_publico_alvo": [],
        "criterios_proponente": [],
        "observacoes": [],
        "raw": content
    }


if __name__ == "__main__":
    print("Token carregado?", bool(HF_TOKEN))

    texto = extrair_texto_pdf("edital.pdf", max_paginas=6)
    resultado = analisar_publico_alvo(texto)

    print("\nResultado:")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
