# IAUPE Analyzer – Pipeline de Análise Automatizada de Editais (FACEPE)

## 📌 Visão Geral

O **IAUPE Analyzer** é um sistema em **pipeline modular** para coleta e análise automatizada de editais publicados no site da FACEPE.

O sistema:

- Coleta automaticamente os links de PDFs de editais
- Extrai texto dos documentos (em memória)
- Envia o conteúdo para um modelo de linguagem (LLM)
- Retorna um JSON estruturado com informações relevantes
- (Opcional) Persiste resultados no **MongoDB** para cache e retomada

O projeto foi organizado seguindo uma **Arquitetura Modular em Pipeline**, separando responsabilidades para facilitar manutenção, substituição de componentes e evolução futura.

---

## 🏗 Arquitetura do Projeto

```text
iaupe-analyser/
│
├── .venv/                  # Ambiente virtual Python
├── pipeline/               # Núcleo principal do sistema
│   ├── services/           # Camada de serviços
│   │   ├── scraper.py      # Coleta links de PDFs
│   │   ├── extractor.py    # Extrai texto dos PDFs
│   │   ├── analyzer.py     # Envia texto ao LLM e retorna JSON
│   │   └── db_mongo.py     # Persistência/caching no MongoDB
│   └── main.py             # Orquestra o pipeline
│
├── sandbox/                # Scripts de apoio/testes (ex.: checagem de cobertura no Mongo)
│   └── check_mongo_coverage.py
│
├── requirements.txt        # Dependências do projeto
├── .env                    # Chaves de API (não versionado)
└── README.md
```

---

## 🧠 Tipo de Arquitetura

**Arquitetura Modular em Pipeline (Data Processing Pipeline)**

Fluxo do sistema:

```text
FACEPE (HTML)
↓
Scraper
↓
Lista de URLs de PDFs
↓
[Opcional] Cache/Persistência (MongoDB)
- se url_pdf já existe com status=ok, pode pular
- se status=erro, o item pode ser reprocessado em outra execução
↓
Extractor (processamento em memória)
↓
Texto extraído
↓
Analyzer (LLM)
↓
JSON estruturado
↓
[Opcional] Salvar/Atualizar no MongoDB (url_pdf único)
↓
Exibido no terminal
```

Cada módulo possui responsabilidade única (Single Responsibility / SOLID).

---

## ⚙️ Componentes do Sistema

### 1️⃣ Scraper (`scraper.py`)

Responsável por:

- Acessar a página de editais da FACEPE
- Identificar botões/links de download
- Coletar links diretos de PDFs
- Retornar lista de URLs

> Não baixa o PDF e não analisa conteúdo.

---

### 2️⃣ Extractor (`extractor.py`)

Responsável por:

- Receber a URL de um PDF
- Fazer download via HTTP
- Processar o PDF em memória (`BytesIO`)
- Extrair texto (via `pdfplumber`)
- Retornar o texto extraído

**Importante:**
- O PDF **não é salvo** no disco
- O processamento é feito inteiramente em memória

---

### 3️⃣ Analyzer (`analyzer.py`)

Responsável por:

- Receber o texto extraído
- Construir prompt estruturado
- Enviar requisição para o provedor de LLM
- Garantir retorno em JSON (ou registrar erro)
- Retornar estrutura padronizada

Exemplo de saída:

```json
{
  "url_pdf": "",
  "publico_alvo": "",
  "descricao": "",
  "criterios_publico_alvo": [],
  "criterios_proponente": [],
  "observacoes": []
}
```

A camada de análise pode ser substituída (OpenAI, HuggingFace, Gemini, etc.) sem alterar o restante do pipeline.

---

### 4️⃣ Persistência/caching (`db_mongo.py`)

Responsável por:

- Salvar o resultado no MongoDB com `url_pdf` como chave única
- Manter um `status` por documento:
  - `ok`: analisado com sucesso
  - `erro`: falhou (ex.: API indisponível/quota, texto vazio, etc.)
- Permitir **retomada** do pipeline:
  - itens com `status=ok` podem ser pulados
  - itens com `status=erro` podem ser reprocessados

---

### 5️⃣ Orquestrador (`main.py`)

Responsável por:

- Orquestrar o pipeline completo
- Definir o `LIMIT` de processamento (`PIPELINE_LIMIT`)
- Executar as etapas na ordem correta
- Exibir os resultados no terminal
- Fazer retry simples em cenários de rate-limit (quando aplicável)

---

## ✅ Script de checagem de cobertura (MongoDB)

O script `sandbox/check_mongo_coverage.py` ajuda a validar o progresso:

- Quantos PDFs existem no site (scraper)
- Quantos já estão no Mongo
- Quantos estão com `status=ok`, `status=erro`
- Quantos ainda faltam

Uso:

```powershell
cd .\sandbox\
python .\check_mongo_coverage.py
```

---

## 📦 Pré-requisitos

- Python 3.10+
- Ambiente virtual configurado
- Chave de API válida do provedor de LLM (ex.: Gemini)
- (Opcional) MongoDB (local ou Atlas) para persistir resultados

---

## 🔧 Instalação

### 1️⃣ Criar ambiente virtual

```powershell
python -m venv .venv
```

### 2️⃣ Ativar ambiente virtual (Windows / PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3️⃣ Instalar dependências

```powershell
pip install -r requirements.txt
```

---

## 🔐 Configuração

Criar arquivo `.env` na raiz do projeto:

```env
GEMINI_API_KEY=sua_chave_aqui
# (fallback aceito pelo código, se você usar esse nome)
# GAMINI_API_KEY=sua_chave_aqui

# (Opcional) Persistência no MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=iaupe-analyser
MONGODB_COLLECTION=editais
```

⚠️ O `.env` **não deve** ser enviado ao GitHub.

---

## ▶️ Como Executar

Com o ambiente virtual ativado:

```powershell
python .\pipeline\main.py
```

---

## 🎛 Controle de Execução (LIMIT)

Por padrão o pipeline processa **todos** os PDFs coletados. Para limitar, use a variável de ambiente `PIPELINE_LIMIT`.

PowerShell (Windows):

```powershell
$env:PIPELINE_LIMIT="5"
python .\pipeline\main.py
```

Para processar todos:

```powershell
$env:PIPELINE_LIMIT="all"
python .\pipeline\main.py
```

---

## ⚠️ Observações sobre quota/rate limit do LLM

Dependendo do plano do provedor de LLM, é possível receber erros como:

- `429 RESOURCE_EXHAUSTED`: limite de quota/rate limit
- `503 UNAVAILABLE`: modelo indisponível (alta demanda)

Nesses casos, o pipeline pode registrar `status=erro` e os itens poderão ser **reprocessados** em outra execução.