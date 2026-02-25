# IAUPE Analyzer – Pipeline de Análise Automatizada de Editais FACEPE

## 📌 Visão Geral

O **IAUPE Analyzer** é um sistema estruturado em **pipeline modular de processamento de dados** para coleta e análise automatizada de editais publicados no site da FACEPE.

O sistema:

- Coleta automaticamente os links de PDFs de editais  
- Extrai o texto das primeiras páginas dos documentos  
- Envia o conteúdo para um modelo de linguagem (LLM)  
- Retorna um JSON estruturado com informações relevantes  

O projeto foi organizado seguindo uma **Arquitetura Modular em Pipeline**, separando responsabilidades para facilitar manutenção, substituição de componentes e evolução futura.

---

## 🏗 Arquitetura do Projeto

```text
iaupe-analyser/
│
├── .venv/ # Ambiente virtual Python
├── pipeline/ # Núcleo principal do sistema
│ ├── services/ # Camada de serviços
│ │ ├── scraper.py # Coleta links de PDFs
│ │ ├── extractor.py # Extrai texto dos PDFs
│ │ └── analyzer.py # Envia texto ao LLM e retorna JSON
│ └── main.py # Orquestra o pipeline
│
├── sandbox/ # Ambiente de testes isolados (ex: 1 PDF)
│
├── requirements.txt # Dependências do projeto
├── .env # Chaves de API (não versionado)
└── README.md
```

---

## 🧠 Tipo de Arquitetura

Este projeto utiliza:

**Arquitetura Modular em Pipeline (Data Processing Pipeline)**

Fluxo do sistema:

```text
FACEPE (HTML)
↓
Scraper
↓
Lista de URLs de PDFs
↓
Extractor (processamento em memória)
↓
Texto extraído
↓
Analyzer (LLM)
↓
JSON estruturado exibido no terminal
```

Cada módulo possui responsabilidade única, seguindo o princípio **Single Responsibility (SOLID)**.

---

## ⚙️ Componentes do Sistema

### 1️⃣ Scraper (`scraper.py`)

Responsável por:

- Acessar a página de editais da FACEPE  
- Identificar botões oficiais de download  
- Coletar links diretos de PDFs  
- Retornar lista de URLs  

**Não baixa o PDF.**  
**Não analisa conteúdo.**  
Apenas coleta os links.

---

### 2️⃣ Extractor (`extractor.py`)

Responsável por:

- Receber a URL de um PDF  
- Fazer download via HTTP  
- Processar o PDF em memória utilizando `BytesIO`  
- Extrair texto das primeiras páginas usando `pdfplumber`  
- Retornar o texto extraído  

**Importante:**  
- O PDF não é salvo no disco  
- O processamento é feito inteiramente em memória  

---

### 3️⃣ Analyzer (`analyzer.py`)

Responsável por:

- Receber o texto extraído  
- Construir prompt estruturado  
- Enviar requisição para o provedor de LLM  
- Garantir que o retorno seja JSON válido  
- Retornar estrutura padronizada  

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

A camada de análise pode ser facilmente substituída para trocar o provedor (OpenAI, HuggingFace, Gemini, etc.) sem alterar o restante da arquitetura.

---

### 4️⃣ Main (`main.py`)

Responsável por:

- Orquestrar o pipeline completo  
- Definir o `LIMIT` de processamento  
- Executar as etapas na ordem correta  
- Exibir os resultados no terminal  

O `LIMIT` controla quantos PDFs serão processados por execução, permitindo:

- Controle de custo (tokens)  
- Controle de tempo  
- Testes rápidos  

---

## 🔄 Funcionamento do Pipeline

- O sistema acessa a URL da FACEPE  
- O scraper coleta todos os links de PDFs disponíveis  
- O sistema seleciona apenas os primeiros `LIMIT` documentos  
- Cada PDF é baixado e processado em memória  
- O texto é enviado ao modelo de linguagem  
- O resultado estruturado é exibido no terminal  

Não há persistência de dados na versão atual.

---

## 📦 Pré-requisitos

- Python 3.10+  
- Ambiente virtual configurado  
- Conta em provedor de LLM (OpenAI, Hugging Face, etc.)  
- Chave de API válida  

---

## 🔧 Instalação

### 1️⃣ Criar ambiente virtual

```bash
python -m venv .venv
```

### 2️⃣ Ativar ambiente virtual

Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3️⃣ Instalar dependências

```bash
pip install -r requirements.txt
```

---

## 🔐 Configuração

Criar arquivo `.env` na raiz do projeto:

```env
OPENAI_API_KEY=sua_chave_aqui
```

⚠️ O `.env` não deve ser enviado ao GitHub.

---

## ▶️ Como Executar

Com o ambiente virtual ativado:

```bash
cd pipeline
python main.py
```

Ou diretamente da raiz:

```bash
python pipeline\main.py
```

---

## 🎛 Controle de Execução

No `main.py`:

```python
LIMIT = 3
```

Altere esse valor para controlar quantos PDFs serão processados por execução.

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