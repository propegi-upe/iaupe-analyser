# iaupe-analyser

Integração em Python para analisar um PDF de edital de fomento e retornar um objeto indicando o público-alvo (e outros campos) usando Hugging Face Router (HF_TOKEN).

## Estrutura

- project/main.py: script principal. Extrai texto do PDF e chama a API.
- project/test_hf.py: valida o token HF (whoami-v2).
- project/.env: armazena HF_TOKEN.
- project/edital.pdf: PDF exemplo.
- requirements.txt: dependências.

## O que foi implementado

- Extração de texto do PDF:
  - Função `extrair_texto_pdf` usando `pdfplumber`, lendo até N páginas e concatenando texto.

- Integração com API (Hugging Face Router):
  - Endpoint: `https://router.huggingface.co/v1/chat/completions`.
  - Autenticação via `HF_TOKEN` do `.env`.
  - Modelo configurável via `HF_MODEL` (default: `mistralai/Mistral-7B-Instruct-v0.2`).
  - Prompt estruturado exigindo resposta somente em JSON com campos:
    - `publico_alvo`, `descricao`,
    - `criterios_publico_alvo`, `criterios_proponente`,
    - `observacoes`.
  - Truncamento opcional do texto (`HF_MAX_PROMPT_CHARS`) para evitar exceder o contexto.

- Tratamento da resposta:
  - Leitura de `choices[0].message.content`.
  - Limpeza de cercas de código (```json ... ```).
  - Fallback com regex para extrair o primeiro bloco `{ ... }`.
  - Fallback final: retorna estrutura vazia com campo `raw` contendo o conteúdo bruto quando não é possível parsear.

## Pré-requisitos

- Python 3.10+
- Dependências:
  - `pdfplumber`, `requests`, `python-dotenv`

Instalação:
```
pip install -r requirements.txt
```

## Configuração

Crie o arquivo `project/.env` com:
```
HF_TOKEN=hf_XXXXXXXXXXXXXXXXXXXXXXXX
```

Valide o token:
```
cd project
python test_hf.py
# Esperado: Status 200 e dados do usuário
```

## Execução

Na pasta `project`:
```
python main.py
```

Saída esperada:
- Um JSON impresso com os campos:
  - `publico_alvo`, `descricao`,
  - `criterios_publico_alvo`, `criterios_proponente`,
  - `observacoes`.
- Se o edital for local e isso estiver descrito no PDF, o texto refletirá nos campos; se não houver menção, campos ficam vazios conforme as regras do prompt.

