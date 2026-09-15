# Import de Docentes (planilha → MongoDB)

Esta pasta guarda a planilha exportada do formulário "Experiência Profissional
Docentes e Servidores da UPE" e o notebook usado para explorá-la. O script que
efetivamente limpa e carrega os dados no MongoDB fica em
[`sandbox/import_docentes_interesse.py`](../sandbox/import_docentes_interesse.py).

## O que o script faz

Lê a planilha `.xlsx`, para cada linha:

1. Normaliza o e-mail (remove espaços, inclusive internos, baixa a caixa) e
   descarta linhas sem e-mail ou com e-mail inválido.
2. Separa a coluna de áreas de interesse contra o catálogo fixo de 8 valores
   usado pelo Gemini para classificar editais
   (`pipeline/pdf_pipeline/analyzer.py::AREAS_INTERESSE`) — os mesmos textos
   usados em `editais.resultado.areas_interesse`, para o matching funcionar.
3. Separa a coluna de segmentos por vírgula.
4. Agrupa por e-mail (a planilha pode ter a mesma pessoa em mais de uma
   linha).

O resultado é gravado na collection `docentes` do MongoDB, identificado por
e-mail (`upsert=True` — rodar de novo não duplica, só atualiza).

## Como rodar

Sempre em modo **dry-run primeiro** (não grava nada, só mostra o resumo):

```powershell
python sandbox/import_docentes_interesse.py
python sandbox/import_docentes_interesse.py --input "dados_docentes/minha_planilha.xlsx"
```

Depois de conferir o resumo, gravar de verdade:

```powershell
python sandbox/import_docentes_interesse.py --apply
```

## Validações e o que o relatório mostra

- **E-mails inválidos ou vazios**: contados em `email_invalido`/`sem_email`,
  descartados (não entram no import).
- **Áreas fora do catálogo oficial**: não são gravadas em `areas_interesse` —
  um docente com uma "área" que o catálogo não reconhece nunca bateria com
  nenhum edital (ver `pipeline/orchestration/docente_match.py`), então esse
  valor fica separado em `areas_rejeitadas`, reportado no resumo, para revisão
  manual (corrigir a planilha e rodar de novo, se for o caso).
- **Duplicatas de e-mail com áreas/segmentos divergentes**: o comportamento
  continua sendo unir os valores das duas linhas, mas agora o e-mail é listado
  em `duplicatas_divergentes` no resumo, para você conferir se a união faz
  sentido ou se é erro de preenchimento na planilha.

## Reprocessar com segurança

O script é idempotente: rodar de novo com a mesma planilha (ou uma versão
atualizada dela) não duplica documentos — cada e-mail é uma chave única, e o
`update_one(..., upsert=True)` substitui `areas_interesse`/`segmentos` pelo
valor mais recente. Sempre rode sem `--apply` primeiro para conferir o
resumo antes de gravar.

## Testes

As funções puras de limpeza (`normalize_email`, `split_areas`,
`split_segmentos`, `build_docentes`) têm testes automatizados em
[`pipeline/tests/test_import_docentes_interesse.py`](../pipeline/tests/test_import_docentes_interesse.py):

```powershell
pip install -r requirements-dev.txt
pytest pipeline/tests/ -v
```
