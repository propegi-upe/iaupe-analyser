
# IAUPE- ANALYSER – Analisador de Editais com LLM

## Objetivo

Este projeto analisa automaticamente um **edital de fomento em PDF** e retorna um **objeto JSON estruturado** contendo:

Fluxo implementado:

PDF → Extração de Texto → Requisição HTTP para API → JSON estruturado


---

## ⚙️ Como Rodar

### 1️⃣ Criar arquivo `.env`

Dentro da pasta `project/`, crie o arquivo:

.env


E adicione:

HF_TOKEN=seu_token_aqui


> ⚠️ O arquivo `.env` não deve ser enviado ao GitHub.

---

### 2️⃣ Instalar dependências

```bash
pip install -r requirements.txt
Ou manualmente:

pip install pdfplumber requests python-dotenv
3️⃣ Executar o projeto
cd project
python main.py
🧰 Tecnologias Utilizadas
Python 3.x

pdfplumber

requests

python-dotenv

Hugging Face Router API (LLM)