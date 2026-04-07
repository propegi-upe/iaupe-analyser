# IAUPE Analyzer - Pipeline de Editais Multi-Fonte

## Visao Geral

O IAUPE Analyzer e um pipeline Python para:

1. Coletar links de editais por fonte.
2. Extrair texto dos documentos PDF.
3. Analisar conteudo com IA (Gemini).
4. Salvar resultados estruturados no MongoDB.

O pipeline de producao esta organizado em modulos por responsabilidade, com orquestracao central e componentes desacoplados.

## Fontes Suportadas

| Fonte  | Chave (`--source`) | Collection Mongo |
|--------|---------------------|------------------|
| FACEPE | `facepe`            | `editais_facepe` |
| CNPq   | `cnpq`              | `editais_cnpq`   |
| FINEP  | `finep`             | `editais_finep`  |
| CAPES  | `capes`             | `editais_capes`  |

## Arquitetura da Pipeline

Fluxo principal:

```text
Fonte selecionada (--source)
-> collect_links (scraper da fonte)
-> extractor (texto do PDF)
-> analyzer (JSON estruturado)
-> save (MongoDB na collection da fonte)
```

Estrutura de producao:

```text
pipeline/
├── main.py                      # entrypoint da CLI
├── orchestration/
│   ├── pipeline_runner.py       # fluxo completo da pipeline
│   ├── source_registry.py       # registro e resolucao de fontes
│   ├── settings.py              # configs de execucao (env/limites/sleeps)
│   ├── retry_policy.py          # retry de erros temporarios do Gemini
│   └── date_parser.py           # parse da data_limit_submissao
├── sources/
│   ├── scraper_facepe.py
│   ├── scraper_cnpq.py
│   ├── scraper_finep.py
│   └── scraper_capes.py
├── pdf_pipeline/
│   ├── extractor.py             # extracao de texto de PDF
│   └── analyzer.py              # analise via Gemini
├── db/
│   └── mongo.py                 # persistencia e cache de conexao MongoDB
└── emails/
	├── email.py
	├── emails_service.py
	├── gmail_smtp_email_service.py
	└── send_email_use_case.py
```

## Requisitos

- Python 3.10+
- Ambiente virtual
- Dependencias em `requirements.txt`
- Chave Gemini valida
- MongoDB (local ou Atlas)

## Instalacao

1. Criar ambiente virtual:

```powershell
python -m venv .venv
```

2. Ativar ambiente virtual (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

3. Instalar dependencias:

```powershell
pip install -r requirements.txt
```

## Configuracao (.env)

Exemplo:

```env
GEMINI_API_KEY=sua_chave_aqui

MONGODB_URI=mongodb+srv://...
MONGODB_DB=iaupe-analyser

PIPELINE_SOURCE=facepe
PIPELINE_LIMIT=all

SLEEP_ALREADY_EXISTS=5
SLEEP_NEW_PROCESS=60
SLEEP_EMPTY_TEXT=5
MAX_RETRIES_GEMINI=3

MONGODB_SERVER_SELECTION_TIMEOUT_MS=30000
MONGODB_CONNECT_TIMEOUT_MS=30000
MONGODB_SOCKET_TIMEOUT_MS=30000

# SMTP (para testes com Mailtrap ou outro servidor SMTP)
SMTP_HOST=sandbox.smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USER=seu_usuario_mailtrap
SMTP_PASS=sua_senha_mailtrap
DEFAULT_EMAIL_FROM=from@example.com

# destinatario padrao de testes
TEST_EMAIL_TO=to@example.com
```

Observacoes:

- A collection no Mongo e definida pela fonte selecionada.
- `MONGODB_COLLECTION` funciona como fallback interno quando nenhuma collection e informada na chamada.
- Para desativar persistencia mesmo com URI definida, use `MONGODB_ENABLED=0`.

## Execucao da Pipeline

Na raiz do projeto:

```powershell
python .\pipeline\main.py --source facepe --limit 10
```

Ou dentro da pasta `pipeline`:

```powershell
python .\main.py --source facepe --limit 10
```

Exemplos:

```powershell
python .\pipeline\main.py --source cnpq
python .\pipeline\main.py --source finep --limit 5
python .\pipeline\main.py --source capes
```

Sem `--source`, o padrao e `facepe`.

## Tratamento de Erros

- Retry de IA para `429` (respeita tempo sugerido na mensagem).
- Retry de IA para `503` (backoff progressivo).
- Falha de Mongo pode desabilitar persistencia sem derrubar toda a execucao.
- Persistencia com insert/update por `url_pdf` (indice unico).

## Como Adicionar Nova Fonte

1. Criar arquivo em `pipeline/sources/`, por exemplo `scraper_nova_fonte.py`.
2. Definir:
   - `SOURCE_KEY`
   - `SOURCE_LABEL`
   - `BASE_URL`
   - `MONGO_COLLECTION`
   - `collect_links(url_lista: str) -> list[str]`
3. Registrar a fonte em `pipeline/orchestration/source_registry.py`.

## Sandbox (Area de Teste de Desenvolvimento)

A pasta `sandbox/` e uma area de teste de desenvolvimento.

Ela existe para validar experimentos sem acoplar direto na pipeline de producao, por exemplo:

- teste de conexao com MongoDB
- teste de Gemini
- teste de envio SMTP (Mailtrap)
- simulacao isolada de notificacoes e workflow de GitHub Actions

Exemplo atual de notificacao em ambiente de teste:

- `sandbox/notification_actions/notify_mailtrap_sandbox.py`
- `sandbox/notification_actions/workflow_notify_mailtrap_sandbox.yml`

## Boas Praticas

- Nao versionar `.env`.
- Nao expor credenciais em commits, logs ou README.
- Rotacionar chaves caso alguma seja exposta.
