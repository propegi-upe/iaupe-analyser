# IAUPE Analyzer - Pipeline de Editais Multi-Fonte

## Visao geral

O IAUPE Analyzer e um pipeline Python para:

1. Coletar links de editais.
2. Extrair texto dos documentos.
3. Analisar o conteudo com IA (Gemini).
4. Salvar resultados estruturados no MongoDB.

O projeto foi evoluido para arquitetura multi-fonte, com alta coesao e baixo acoplamento.
O pipeline principal e unico, e cada fonte tem seu proprio modulo de scraping.

## O que foi adicionado

- Suporte a multiplas fontes via parametro `--source` e variavel `PIPELINE_SOURCE`.
- Separacao da camada de scraping por fonte em `pipeline/sources/`.
- Collections separadas no MongoDB por fonte.
- Persistencia dinamica por collection em `db/mongo.py`.
- Script de cobertura no MongoDB por fonte em `sandbox/check_mongo_coverage.py`.

## Fontes suportadas

| Fonte  | Chave (`--source`) | Collection Mongo   | 
|-------|---------------------|--------------------|
| FACEPE | `facepe`            | `editais_facepe`   |
| CNPq   | `cnpq`              | `editais_cnpq`     |
| FINEP  | `finep`             | `editais_finep`    |
| CAPES  | `capes`             | `editais_capes`    | 

## Estrutura do projeto

```text
iaupe-analyser/
├── pipeline/
│   ├── main.py
│   ├── pdf_pipeline/
│   │   ├── analyzer.py
│   │   └── extractor.py
│   ├── db/
│   │   └── mongo.py
│   ├── emails/
│   │   ├── email.py
│   │   ├── emails_service.py
│   │   ├── gmail_smtp_email_service.py
│   │   └── send_email_use_case.py
│   └── sources/
│       ├── scraper_facepe.py
│       ├── scraper_cnpq.py
│       ├── scraper_finep.py
│       └── scraper_capes.py
├── sandbox/
│   ├── check_mongo_coverage.py
│   ├── test_email_mailtrap.py
│   └── test_email_edital_flow.py
├── requirements.txt
├── .env
└── README.md
```

## Arquitetura

Fluxo principal:

```text
Fonte selecionada (--source)
-> collect_links (modulo da fonte)
-> extractor (texto do edital)
-> analyzer (JSON estruturado)
-> save no MongoDB (collection da fonte)
```

Separacao de responsabilidades:

- `pipeline/main.py`: orquestracao e controle de execucao.
- `pipeline/sources/*.py`: scraping por fonte (HTML especifico).
- `pipeline/pdf_pipeline/extractor.py`: download e extracao de texto.
- `pipeline/pdf_pipeline/analyzer.py`: prompt e analise com Gemini.
- `pipeline/db/mongo.py`: cache e persistencia no MongoDB.
- `pipeline/emails/*`: entidade, contrato, servico SMTP e use case de email.

## Requisitos

- Python 3.10+
- Ambiente virtual
- Dependencias em `requirements.txt`
- Chave Gemini valida
- MongoDB opcional (local ou Atlas)

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

# smtp (para testes com mailtrap ou qualquer servidor smtp)
SMTP_HOST=sandbox.smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USER=seu_usuario_mailtrap
SMTP_PASS=sua_senha_mailtrap
DEFAULT_EMAIL_FROM=from@example.com

# opcional: destinatario padrao de testes
TEST_EMAIL_TO=to@example.com
```

Observacoes:

- No pipeline principal, a collection vem da fonte selecionada.
- `MONGODB_COLLECTION` e apenas fallback interno quando nenhuma collection e informada na chamada.
- Para desativar persistencia mesmo com URI definida, use `MONGODB_ENABLED=0`.

## Como executar

Na raiz do projeto:

```powershell
python .\pipeline\main.py --source facepe
```

Ou dentro da pasta `pipeline`:

```powershell
python .\main.py --source facepe
```

Exemplos:

```powershell
python .\main.py --source cnpq
python .\main.py --source facepe --limit 10
python .\main.py --source finep
python .\main.py --source capes
```

Sem `--source`, o padrao e `facepe`.

## Testes de email (Mailtrap)

Esta secao serve para validar o modulo de emails em ambiente de testes (sem enviar para usuarios reais).
O Mailtrap funciona como um "sandbox" que captura os emails enviados via SMTP e mostra em uma inbox de testes.

### 1) Teste simples de envio SMTP

Arquivo: `sandbox/test_email_mailtrap.py`

Para que serve:
- valida que o SMTP esta configurado e que o envio basico funciona.

Como rodar (na raiz do projeto):

```powershell
python .\sandbox\test_email_mailtrap.py
```

O que esperar:
- o script imprime uma mensagem de sucesso.
- o email aparece na inbox do Mailtrap.

### 2) Teste de fluxo completo (edital -> analise -> email)

Arquivo: `sandbox/test_email_edital_flow.py`

Para que serve:
- coleta um edital real (via scraper), extrai texto do PDF, analisa com Gemini e envia um relatorio padronizado por email.

Como rodar (na raiz do projeto):

```powershell
python .\sandbox\test_email_edital_flow.py --source capes --max-pages 2 --to to@example.com
```

Alternativas:
- trocar fonte: `--source facepe` / `--source cnpq` / `--source finep`
- informar um PDF direto: `--pdf-url https://...pdf`

## Collections por fonte

- `facepe` -> `editais_facepe`
- `cnpq` -> `editais_cnpq`
- `finep` -> `editais_finep`
- `capes` -> `editais_capes`

## Script de cobertura no MongoDB

Arquivo: `sandbox/check_mongo_coverage.py`

Funcao:

- Coleta links da fonte selecionada.
- Consulta a collection da mesma fonte.
- Mostra total, `ok`, `erro` e faltantes.

Uso:

```powershell
python .\sandbox\check_mongo_coverage.py --source facepe
python .\sandbox\check_mongo_coverage.py --source cnpq
```

## Tratamento de erros

- Retry de IA para `429` (respeitando tempo sugerido).
- Retry de IA para `503` (espera progressiva).
- Falha no Mongo nao derruba o pipeline.
- Upsert por `url_pdf` com status (`ok` ou `erro`).

## Como adicionar nova fonte

1. Criar arquivo em `pipeline/sources/`, por exemplo `scraper_nova_fonte.py`.
2. Definir:
- `SOURCE_KEY`
- `SOURCE_LABEL`
- `BASE_URL`
- `MONGO_COLLECTION`
- `collect_links(url_lista: str) -> list[str]`
3. Registrar a nova fonte no `SOURCE_REGISTRY` de `pipeline/main.py`.
4. Registrar a nova fonte no `SOURCE_REGISTRY` de `sandbox/check_mongo_coverage.py`.

## Boas praticas

- Nao versionar `.env`.
- Nao expor credenciais em prints, README ou commits.
- Rotacionar chaves caso alguma tenha sido exposta.
