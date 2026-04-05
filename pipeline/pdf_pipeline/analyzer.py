import os
import json
import re
from dotenv import load_dotenv
from google import genai

MODEL = "gemini-2.5-flash"

AREAS_INTERESSE = [
    "Projetos de Pesquisa, Desenvolvimento e Inovação (PD&I)",
    "Extensão Tecnológica (prestação de serviços, assistência tecnológica)",
    "Empreendedorismo (apoio a startups, spin-offs)",
    "Incubação de Empresas",
    "Aceleração de Negócios",
    "Serviços Tecnológicos",
    "Propriedade Intelectual (patentes, licenciamento, transferência de tecnologia)",
    "Captação de Recursos para PD&I/Inovação",
]

SEGMENTOS = [
    "Saúde",
    "Educação",
    "Indústria",
    "Comércio",
    "Serviços",
    "Agropecuária",
    "Tecnologia da informação(TI)",
    "Construção civil",
    "Transporte e Logística",
    "Administração pública",
]


def get_api_key() -> str | None:
    load_dotenv(override=True)
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GAMINI_API_KEY") or "").strip() or None


def call_gemini(client: genai.Client, model: str, prompt: str) -> str:
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
    api_key = get_api_key()
    if not api_key:
        return {"erro": "Defina GEMINI_API_KEY no .env ou no ambiente"}

    client = genai.Client(api_key=api_key)

    prompt = f"""
Você é um analista de editais.

Sua tarefa é ler o conteúdo do edital e responder SOMENTE com JSON válido.

Regras importantes:

1. Não invente informações.
2. Preencha os campos textuais com base no edital.
3. Os campos "areas_interesse", "segmentos" e "cronograma" devem ser arrays.
4. Nos campos "areas_interesse" e "segmentos", use SOMENTE valores exatamente iguais aos permitidos abaixo.
5. Um edital deve possuir OBRIGATORIAMENTE pelo menos uma "area_interesse".
6. Um edital deve possuir OBRIGATORIAMENTE pelo menos um "segmento".
7. A classificação de "areas_interesse" e "segmentos" deve ser baseada em evidência EXPLÍCITA no edital (ex: público-alvo, objetivo, área de atuação, aplicação do projeto).
8. NÃO faça inferências amplas ou suposições. Seja conservador e preciso.
9. Caso o edital seja genérico, escolha a categoria MAIS SEGURA e MAIS DIRETA com base no foco principal do edital.
10. NÃO deixe "areas_interesse" ou "segmentos" vazios em hipótese alguma.
11. O campo "cronograma" deve conter os principais marcos, etapas, datas, prazos, resultados, recursos, contratação e demais eventos temporais do edital.
12. Cada item de "cronograma" deve ser uma string clara e objetiva.
13. Se não houver informações de cronograma no edital, retorne "cronograma": [].
14. O campo "data_limit_submissao" deve vir no formato YYYY-MM-DD com a data limite de submissão do edital.
15. Se não houver data limite de submissão explícita, retorne "data_limit_submissao": "".
16. Não retorne nenhum texto fora do JSON.

ÁREAS DE INTERESSE PERMITIDAS:
{json.dumps(AREAS_INTERESSE, ensure_ascii=False, indent=2)}

SEGMENTOS PERMITIDOS:
{json.dumps(SEGMENTOS, ensure_ascii=False, indent=2)}

Responda no formato:

{{
  "url_pdf": "{pdf_url}",
  "publico_alvo": "",
  "descricao": "",
  "criterios_publico_alvo": [],
  "criterios_proponente": [],
  "observacoes": [],
  "areas_interesse": [],
  "segmentos": [],
    "cronograma": [],
    "data_limit_submissao": ""
}}

Edital:
{text}
""".strip()

    try:
        content = call_gemini(client, MODEL, prompt)
    except Exception as e:
        msg = str(e)
        if "API_KEY_INVALID" in msg or "API key not valid" in msg:
            return {
                "erro": "API key inválida. Gere uma nova no Google AI Studio e atualize o .env",
                "raw": msg,
            }
        if "models/" in msg and "not found" in msg.lower():
            try:
                content = call_gemini(client, "gemini-flash-latest", prompt)
            except Exception as e2:
                return {"erro": "Modelo Gemini indisponível", "raw": str(e2)}
        else:
            return {"erro": "Falha ao chamar Gemini", "raw": msg}

    try:
        data = json.loads(content)
    except Exception:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
            except Exception:
                return {"erro": "JSON inválido", "raw": content}
        else:
            return {"erro": "JSON inválido", "raw": content}

    data.setdefault("url_pdf", pdf_url)
    data.setdefault("publico_alvo", "")
    data.setdefault("descricao", "")
    data.setdefault("criterios_publico_alvo", [])
    data.setdefault("criterios_proponente", [])
    data.setdefault("observacoes", [])
    data.setdefault("areas_interesse", [])
    data.setdefault("segmentos", [])
    data.setdefault("cronograma", [])
    data.setdefault("data_limit_submissao", "")

    data["areas_interesse"] = list(dict.fromkeys(
        item for item in data.get("areas_interesse", [])
        if item in AREAS_INTERESSE
    ))

    data["segmentos"] = list(dict.fromkeys(
        item for item in data.get("segmentos", [])
        if item in SEGMENTOS
    ))

    if not isinstance(data.get("cronograma"), list):
        data["cronograma"] = []

    data["cronograma"] = list(dict.fromkeys(
        str(item).strip()
        for item in data.get("cronograma", [])
        if str(item).strip()
    ))

    data["data_limit_submissao"] = str(data.get("data_limit_submissao") or "").strip()

    return data
