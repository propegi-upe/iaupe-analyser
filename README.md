# IAUPE-ANALYSER – Analisador de Editais com LLM

## Objetivo

Este projeto analisa automaticamente um **edital de fomento em PDF** e retorna um **objeto JSON estruturado** contendo:

Fluxo implementado:

**PDF → Extração de Texto → Requisição HTTP para API (LLM) → JSON estruturado**

## Estrutura (arquivos principais)

- `project/main.py`: fluxo principal (extrai texto do PDF, chama a API e faz o parse do JSON).
- `project/test_hf.py`: teste rápido para validar se o `HF_TOKEN` está funcionando.
- `project/.env`: arquivo local com o token (não versionar).
- `requirements.txt`: dependências do Python.

---

## Como rodar

### 1) Criar arquivo `.env`

Dentro da pasta `project/`, crie o arquivo `project/.env` e adicione:

```env
HF_TOKEN=seu_token_aqui
```

> O arquivo `.env` não deve ser enviado ao GitHub.

---

### 2) Instalar dependências

Na raiz do repositório:

```bash
pip install -r requirements.txt
```

---

### 3) Executar o projeto

Coloque o PDF como `project/edital.pdf` (ou ajuste o nome no código) e rode:

```bash
cd project
python main.py
```

---

## Tecnologias utilizadas

- Python 3.x
- `pdfplumber`
- `requests`
- `python-dotenv`
- Hugging Face Router API (LLM)