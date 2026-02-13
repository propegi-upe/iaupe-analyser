import pdfplumber
import requests
import os
import json
import re
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Carregamento de configuração (variáveis de ambiente)
# -----------------------------------------------------------------------------
# Lê o arquivo "project/.env" (se existir) e injeta as variáveis no ambiente.
# Ex.: HF_TOKEN=...
load_dotenv()

# Token de acesso à Hugging Face (Router API). Deve estar no .env.
HF_TOKEN = os.getenv("HF_TOKEN")


def extrair_texto_pdf(caminho_pdf, max_paginas=5):
    """
    Extrai texto de um PDF usando pdfplumber.

    Args:
        caminho_pdf (str): caminho do PDF (ex.: "edital.pdf")
        max_paginas (int): limita o número de páginas lidas para evitar prompts grandes

    Returns:
        str: texto concatenado das páginas (com quebras de linha)
    """
    texto = ""
    # Abre o PDF e percorre as páginas.
    with pdfplumber.open(caminho_pdf) as pdf:
        for i, pagina in enumerate(pdf.pages):
            # Para quando atingir o limite de páginas (controle de custo/latência e contexto).
            if i >= max_paginas:
                break
            # extract_text() pode retornar None dependendo da página, por isso "or ''".
            texto += (pagina.extract_text() or "") + "\n"
    return texto.strip()


def analisar_publico_alvo(texto_edital):
    """
    Envia o texto do edital para um LLM (via Hugging Face Router) pedindo um JSON estruturado.

    Estratégia:
      - Monta um prompt com regras bem explícitas
      - Chama o endpoint /v1/chat/completions
      - Tenta fazer json.loads do retorno
      - Se o modelo "vazar" texto extra, tenta extrair o primeiro bloco { ... } via regex
      - Se falhar, retorna estrutura vazia + campo raw com o conteúdo original

    Args:
        texto_edital (str): texto bruto extraído do PDF

    Returns:
        dict: objeto com o formato especificado no prompt
    """
    # Falha cedo se o token não estiver configurado.
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN não encontrado no .env")

    # Endpoint padrão compatível com OpenAI Chat Completions, porém via Router da HF.
    url = "https://router.huggingface.co/v1/chat/completions"

    # Prompt: define papel, tarefa, formato do JSON e regras.
    # Observação: aqui a instrução mais importante é "Responda SOMENTE com JSON".
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

    # Cabeçalhos HTTP: autenticação via Bearer token + envio de JSON.
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }

    # Corpo da requisição no formato de chat:
    # - model: LLM escolhido no Router
    # - messages: system orienta formato; user contém o prompt com o edital
    # - temperature=0: reduz variação e ajuda a manter consistência/JSON válido
    body = {
        "model": "mistralai/Mistral-7B-Instruct-v0.2",
        "messages": [
            {"role": "system", "content": "Responda apenas JSON válido no formato solicitado. Sem texto extra."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 900,
    }

    # Envia a requisição ao Router (timeout para não travar indefinidamente).
    resp = requests.post(url, headers=headers, json=body, timeout=60)

    # Se a API respondeu erro HTTP, interrompe com detalhe.
    if not resp.ok:
        raise RuntimeError(f"Hugging Face {resp.status_code}: {resp.text}")

    # Interpreta a resposta JSON da API.
    result = resp.json()

    # Estrutura típica: choices[0].message.content contém o texto do modelo.
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

    # -----------------------------------------------------------------------------
    # Parse "robusto": tenta primeiro o caminho ideal (conteúdo é JSON puro).
    # Se vier "lixo" antes/depois, tenta extrair o primeiro bloco { ... }.
    # -----------------------------------------------------------------------------
    try:
        return json.loads(content)
    except Exception:
        # Regex gulosa (com DOTALL) para pegar um objeto JSON multilinha.
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass

    # Se tudo falhar, devolve estrutura vazia e preserva o retorno bruto em "raw"
    # para depuração (ajuda a entender o que o modelo respondeu).
    return {
        "publico_alvo": "",
        "descricao": "",
        "criterios_publico_alvo": [],
        "criterios_proponente": [],
        "observacoes": [],
        "raw": content
    }


if __name__ == "__main__":
    # Debug rápido: confirma se o token foi carregado.
    print("Token carregado?", bool(HF_TOKEN))

    # 1) Extrai texto do PDF (limite de páginas ajustável).
    texto = extrair_texto_pdf("edital.pdf", max_paginas=6)

    # 2) Envia para o LLM e recebe o dicionário estruturado.
    resultado = analisar_publico_alvo(texto)

    # 3) Imprime JSON formatado (indentado) preservando acentos (ensure_ascii=False).
    print("\nResultado:")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
