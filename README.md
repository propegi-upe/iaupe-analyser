# <img width="30" height="30" alt="image" src="https://github.com/user-attachments/assets/f0b62fea-7617-4b5f-b298-4446b3995eff" /> IAUPE Analyzer - Pipeline de Editais Multi-Fonte

## Visão Geral

O IAUPE Analyzer é um pipeline Python para:

1. Coletar links de editais por fonte.
2. Extrair texto de documentos PDF ou páginas HTML.
3. Analisar conteúdo com IA (Gemini).
4. Salvar resultados estruturados no MongoDB.
5. Enviar notificações por e-mail para editais novos e lembretes de prazo.

O pipeline de produção é organizado em módulos por responsabilidade, com orquestração central e fontes plugáveis.

## Fontes Suportadas

Todas as fontes gravam na mesma collection Mongo (`editais`), identificadas pelo campo `fonte`.

| Fonte  | Chave (`--source`) | Campo `fonte` no Mongo |
|--------|---------------------|------------------------|
| FACEPE | `facepe`            | `"facepe"`             |
| CNPq   | `cnpq`              | `"cnpq"`                |
| FINEP  | `finep`             | `"finep"`              |
| CAPES  | `capes`             | `"capes"`              |

Até 2026-07-21 cada fonte gravava numa collection própria (`editais_facepe`,
`editais_cnpq`, `editais_finep`, `editais_capes`). Os dados já foram migrados (via
script one-shot, removido do repo depois de usado) para a collection única `editais`.
As collections antigas foram mantidas como backup no Atlas e podem ser removidas
manualmente após confirmar que tudo continua funcionando na nova.

## Arquitetura da Pipeline

Fluxo principal:

```text
Fonte selecionada (--source)
-> collect_calls (scraper da fonte: url + data de publicação)
-> extractor (texto do PDF/HTML)
-> analyzer (JSON estruturado via Gemini)
-> save (MongoDB na collection da fonte)
-> e-mail (quando o registro é novo e válido)
```

Estrutura de produção:

```text
pipeline/
|-- main.py                         # entrypoint da CLI
|-- orchestration/
|   |-- pipeline_runner.py           # fluxo completo da pipeline
|   |-- deadline_reminder_runner.py  # fluxo de lembretes (D-30, D-15, D-7)
|   |-- source_registry.py           # registro e resolução de fontes
|   |-- settings.py                  # configurações de execução (env/limites/sleeps)
|   |-- retry_policy.py              # retry de erros temporários do Gemini
|   `-- date_parser.py               # parse da data_limit_submissao
|-- sources/
|   |-- facepe/                      # scraper modularizado da FACEPE
|   |-- cnpq/                        # scraper modularizado do CNPq
|   |-- finep/                       # scraper modularizado da FINEP
|   |-- capes/                       # scraper modularizado da CAPES
|   |-- scraper_facepe.py            # wrapper de compatibilidade
|   |-- scraper_cnpq.py              # wrapper de compatibilidade
|   `-- scraper_capes.py             # wrapper de compatibilidade
|-- pdf_pipeline/
|   |-- extractor.py                 # extração de texto de PDF/HTML
|   `-- analyzer.py                  # análise via Gemini
|-- db/
|   `-- mongo.py                     # persistência e cache de conexão MongoDB
`-- emails/
    |-- date_format.py
    |-- email.py
    |-- emails_service.py
    |-- smtp_email_service.py
    |-- send_email_use_case.py
    |-- saved_record_email_notifier.py
    `-- deadline_reminder_email_notifier.py
```

## Fontes Modularizadas

As fontes principais ficam em pacotes dentro de `pipeline/sources/`. Cada pacote expõe uma API pública pelo `__init__.py`, usada pelo `source_registry`.

Estrutura padrão dos pacotes:

- `constants.py`: chave da fonte, label, URL base, collection Mongo e constantes de coleta.
- `client.py`: comunicação HTTP/API da fonte.
- `models.py`: objetos internos usados para ordenar e filtrar documentos.
- `parser.py`: leitura do HTML/API e transformação em objetos estruturados.
- `policy.py`: regras de negócio da fonte, como ano-alvo e filtro de edital principal.
- `scraper.py`: orquestração final e função `collect_links()`.
- `__init__.py`: API pública do pacote.

Os arquivos `scraper_facepe.py`, `scraper_cnpq.py` e `scraper_capes.py` existem apenas como wrappers de compatibilidade para imports antigos.

## Frontend (Next.js)

Além do pipeline Python, o projeto tem um frontend em `front/` que implementa a
funcionalidade de **editais de interesse**: o pesquisador digita só o próprio e-mail
(sem cadastro, sem senha) e marca os editais específicos que quer acompanhar. Os
lembretes de prazo (D-30, D-15, D-7) chegam individualmente para cada e-mail, só dos
editais que aquela pessoa marcou.

- Stack: Next.js 14 (App Router) + React 18 + TypeScript, sem dependências de UI externas.
- Módulo **independente** do pipeline. O único ponto de integração é o MongoDB
  compartilhado: o front lê as collections `editais_*` e grava o e-mail da pessoa no
  campo `interessados` do edital específico marcado — mesmo campo que a pipeline lê
  para saber quem notificar.
- Identificação sem autenticação: o e-mail digitado fica salvo no navegador
  (localStorage), sem senha nem verificação. Cada edital guarda sua própria lista de
  e-mails interessados; a API nunca expõe essa lista inteira para o navegador, só
  responde "esse e-mail específico está inscrito nesse edital?".
- Camadas separadas (`domain` -> `lib` -> `api`/`components`) para alta coesão e baixo
  acoplamento.
- Sem dado fictício: se `MONGODB_URI` não estiver configurado ou a conexão falhar, a tela
  mostra o estado "fora do ar" (selo `AO VIVO`/`FORA DO AR` no topo), nunca um mock.

Execução rápida:

```powershell
cd front
npm install
npm run dev
```

Acesse http://localhost:3000. Detalhes de arquitetura, fluxo do código e endpoints em
[`front/README.md`](front/README.md).

## Regras de Coleta Recente

A regra principal é simples:

1. Cada source coleta os editais e devolve os links já priorizados.
2. O `pipeline_runner` percorre essa lista em ordem.
3. Links já salvos com `status=ok` no MongoDB são ignorados.
4. A pipeline seleciona apenas os primeiros links novos até atingir o limite configurado.

Trecho central em `pipeline/orchestration/pipeline_runner.py`:

```python
calls = source["collect_calls"](source["base_url"])          # [(url_pdf, data_publicacao), ...]
links = [url for url, _ in calls]
data_publicacao_por_url = dict(calls)

pending_links: list[str] = []
for link in links:
    if already_exists(link):                                  # já salvo com status=ok
        already_saved_total += 1
        continue

    pending_links.append(link)
    if limit is not None and len(pending_links) >= limit:
        break

links = pending_links
```

Em resumo: a source organiza os editais por prioridade/recência, e o runner filtra o que já existe no banco para processar somente os próximos editais novos.

Responsabilidades:

- `collect_calls()`: busca os editais da fonte e devolve pares `(url_pdf, data_publicacao)` na ordem esperada. `collect_links()` continua existindo e devolve só as URLs.
- `already_exists()`: consulta o MongoDB para verificar se o PDF já foi processado com `status=ok`.
- `pipeline_runner.py`: aplica o limite da execução, define quais links serão processados e repassa a `data_publicacao` de cada um para o `save()`.

A `data_publicacao` é gravada no documento do edital e usada pelo front para
ordenar a vitrine na mesma ordem do site oficial (mais recente primeiro). CNPq
não expõe essa data (vem `None`); nesse caso, e para editais salvos antes do
campo existir, o front cai no `created_at`.

Regras por fonte:

- FACEPE: coleta somente editais principais do ano-alvo, remove documentos acessórios e ordena por data de publicação mais recente. Data de publicação: extraída de textos como "28 de maio de 2026".
- CNPq: coleta chamadas abertas, lê a data inicial de inscrição quando disponível e prioriza chamadas com inscrição mais recente. Não expõe data de publicação (`data_publicacao` fica `None`).
- FINEP: usa a API da FINEP com `sort=dataDePublicacao:desc`, filtra chamadas abertas e limita as 8 chamadas mais recentes. Data de publicação: campo `dateCreated` da API.
- CAPES: segue a ordem oficial da seção "Editais Abertos", filtra apenas editais principais do ano-alvo e ignora documentos auxiliares. Data de publicação: primeira coluna da tabela de editais (dd/mm/AAAA). URLs de PDF são normalizadas (sem o sufixo `/@@display-file/file` do Plone) para não duplicar o mesmo edital.

Variáveis opcionais para testes ou execuções controladas:

```env
FACEPE_TARGET_YEAR=2026
CAPES_TARGET_YEAR=2026
```

## Requisitos

- Python 3.10+
- Ambiente virtual
- Dependências em `requirements.txt`
- Chave Gemini válida
- MongoDB (local ou Atlas)

## Instalação

1. Criar ambiente virtual:

```powershell
python -m venv .venv
```

2. Ativar ambiente virtual (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

3. Instalar dependências:

```powershell
pip install -r requirements.txt
```

## Configuração (.env)

Veja [`pipeline/.env.example`](pipeline/.env.example) para o template completo
de variáveis (copie para `.env` na raiz do projeto e preencha com valores
reais). Exemplo resumido:

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

SMTP_HOST=sandbox.smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USER=seu_usuario_mailtrap
SMTP_PASS=sua_senha_mailtrap
SENDER_EMAIL=from@example.com
RECIPIENT_EMAIL=to@example.com
```

Observações:

- Todos os editais (de qualquer fonte) ficam numa única collection `editais`; cada
  documento tem um campo `fonte` (`facepe`/`cnpq`/`finep`/`capes`) para identificar a origem.
- Para desativar a persistência mesmo com URI definida, use `MONGODB_ENABLED=0`.
- O remetente do e-mail é definido por `SENDER_EMAIL`.
- `RECIPIENT_EMAIL` aceita um ou vários e-mails separados por vírgula. Quando há
  vários, o e-mail institucional vai com todos em cópia (Cc). A notificação dos
  docentes é separada e vai em cópia **oculta** (BCC) — ver "Notificação de
  Editais Novos por Área/Segmento".
- `SMTP_BCC_BATCH_SIZE` (padrão 90) e `SMTP_SEND_DELAY_SECONDS` (padrão 1.0)
  controlam o envio em BCC: destinatários por mensagem e pausa entre mensagens.

## Execução da Pipeline

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

Sem `--source`, o padrão é `facepe`.

## Automação no GitHub Actions

Workflow principal:

- `.github/workflows/pipeline_runner_daily.yml`
- Agendado diariamente.
- Roda as fontes configuradas em `PIPELINE_SOURCES`.
- Por padrão, processa `1` edital por fonte por dia (`PIPELINE_LIMIT_PER_SOURCE=1`) para reduzir o risco de estourar a quota do Gemini.

Fluxo de envio:

1. O scraper devolve links ordenados conforme a regra da fonte.
2. A pipeline pula links já salvos com `status=ok`.
3. O primeiro link pendente dentro do limite é processado.
4. Se o registro for `inserted` e a análise não tiver erro, o e-mail HTML é enviado —
   esse aviso de "edital novo" **não é filtrado por fonte seguida** (é descoberta, não
   ação urgente); quem é filtrado por fonte seguida é o lembrete de prazo, abaixo.

## Lembretes de Prazo (D-30, D-15, D-7)

O projeto possui um fluxo dedicado para notificações de prazo de submissão.

Como funciona:

1. Busca editais com `status=ok` e `data_limit_submissao` na janela dos marcos configurados.
2. Calcula os dias restantes para o prazo.
3. Para cada edital com prazo batendo, olha a lista `interessados` (e-mails que
   marcaram aquele edital específico, gravada pelo front). Sem ninguém inscrito, pula.
4. Envia um e-mail **individual** para cada interessado (nunca em cópia/Cc — uma
   pessoa não vê o e-mail de outra que também acompanha o mesmo edital).
5. Marca no MongoDB em `deadline_reminder.sent_steps` para evitar reenvio duplicado.

Gerenciar interessados por edital pela linha de comando (sem depender do front):

```powershell
python .\pipeline\main.py --source facepe --add-interessado --url "https://.../edital.pdf" --email "pessoa@exemplo.com"
python .\pipeline\main.py --source facepe --remove-interessado --url "https://.../edital.pdf" --email "pessoa@exemplo.com"
python .\pipeline\main.py --source facepe --list-interessados --url "https://.../edital.pdf"
```

Execução local dos lembretes:

```powershell
python .\pipeline\main.py --source cnpq --run-reminders --reminder-steps 30,15,7
```

Exemplo para somente D-7:

```powershell
python .\pipeline\main.py --source cnpq --run-reminders --reminder-steps 7
```

Automação dos lembretes:

- Workflow: `.github/workflows/deadline-reminders.yml`
- Agendado diariamente e com suporte a disparo manual (`workflow_dispatch`).

## Notificação de Editais Novos por Área/Segmento

Cada docente escolhe na plataforma as **áreas de interesse** e os **segmentos** que
acompanha (tela "Minhas áreas de interesse", gravada na collection `docentes`). A
pipeline usa isso para avisar só quem tem a ver com o edital.

São três disparos, não confundir — os dois primeiros são **o mesmo e-mail**
(`SavedRecordEmailNotifier`), só muda o destinatário:

| Disparo | Quando | Para quem |
| --- | --- | --- |
| Edital novo (institucional) | edital novo salvo | `RECIPIENT_EMAIL` — um endereço que recebe **tudo** |
| **Edital novo por preferência** | edital novo salvo | cada docente cujas áreas/segmentos casam com o edital |
| Lembrete de prazo | D-30/D-15/D-7 | quem marcou interesse **naquele** edital |

Como funciona a notificação por preferência:

1. Ao salvar um edital novo com análise ok e prazo aberto, a pipeline carrega uma
   única vez a lista de docentes com preferência cadastrada.
2. Cruza `resultado.areas_interesse` e `resultado.segmentos` do edital com as
   preferências do docente. A regra é **OU**: basta uma área **ou** um segmento em
   comum. Edital sem classificação nenhuma não notifica ninguém.
3. A comparação é normalizada (sem espaços, sem diferença de caixa), então valores
   legados da planilha como `"Tecnologia da informação( TI)"` casam com o
   `"Tecnologia da informação(TI)"` do catálogo atual.
4. Envia **um único e-mail** com todos os docentes que casam em **cópia oculta
   (BCC)** — mesmo layout que vai para o endereço institucional. Ninguém vê o
   endereço de ninguém (o header `Bcc` nunca vai na mensagem, só a lista do
   envelope). O Google Workspace aceita ~100 destinatários por mensagem, então a
   lista é fatiada em blocos de `SMTP_BCC_BATCH_SIZE` (padrão 90). Cada docente
   que recebeu é marcado em `match_notification.sent_emails`, no próprio documento
   do edital: reprocessar a fonte não reenvia para quem já recebeu; um bloco que
   falha não é marcado e reentra na próxima execução manual.

Travas de volume (a base tem ~260 docentes e dezenas de editais com prazo aberto):

- No máximo **3 e-mails por docente por execução** e um teto total por execução
  (`--max-emails`, padrão 300). Limitam quantos **destinatários** entram por
  rodada — protegem o teto de ~2.000/dia do Workspace. O que passar disso não é
  marcado e entra na próxima rodada.
- `NOTIFY_DOCENTES=0` no `.env`/secrets desliga o envio sem parar a coleta.

Varredura avulsa (`main.py --notify-editais`) — reconcilia "editais salvos" com
"docentes notificados" sempre que os dois divergem: primeiro disparo depois de
popular a base de preferências, docente que cadastra preferências depois de o
edital já existir, drenar um acúmulo de editais (a trava de 3/docente por
execução é por rodada, então um lote grande leva algumas rodadas), ou reprocessar
após falha de SMTP. Roda no dia a dia pelo workflow `notify-editais-daily.yml`
(agendado, logo após a pipeline principal) e também sob demanda:

```powershell
# simulação: mostra quem receberia o quê, não envia nada
python .\pipeline\main.py --notify-editais --source all

# envio real, respeitando as travas
python .\pipeline\main.py --notify-editais --source all --apply

# ajustando os limites da execução
python .\pipeline\main.py --notify-editais --source all --apply --max-por-docente 1 --max-emails 100
```

Conferência detalhada (par a par, sem enviar): `sandbox/test_new_edital_notification.py`.

A carga inicial (e recargas) da base de preferências dos docentes, a partir da
planilha institucional, está documentada em
[`dados_docentes/README.md`](dados_docentes/README.md).

## Tratamento de Erros

- Retry de IA para `429` (respeita o tempo sugerido na mensagem).
- Retry de IA para `503` (backoff progressivo).
- Falha de MongoDB pode desabilitar a persistência sem derrubar toda a execução.
- Persistência com insert/update por `url_pdf` (índice único).
- Falhas em subpáginas de fontes externas podem ser ignoradas com log quando não impedem a coleta dos demais editais.

## Como Adicionar Nova Fonte

1. Criar um pacote em `pipeline/sources/nova_fonte/`.
2. Definir pelo menos:
   - `SOURCE_KEY`
   - `SOURCE_LABEL`
   - `BASE_URL`
   - `collect_calls(url_lista: str) -> list[tuple[str, datetime | None]]` — pares `(url_pdf, data_publicacao)` na ordem da fonte. Use `None` na data quando a fonte não publicar essa informação.
   - `collect_links(url_lista: str) -> list[str]` — normalmente só `[url for url, _ in collect_calls(...)]`.
3. Expor a API pública em `pipeline/sources/nova_fonte/__init__.py` (incluindo `collect_calls`).
4. Registrar a fonte em `pipeline/orchestration/source_registry.py` com as chaves `collect_links` e `collect_calls`.

## Testes automatizados

Testes unitários (pytest) das partes puras da pipeline — matching de docentes,
travas de volume de notificação e limpeza do import de docentes — ficam em
`pipeline/tests/`:

```powershell
pip install -r requirements-dev.txt
pytest pipeline/tests/ -v
```

Isso é diferente da pasta `sandbox/` abaixo, que guarda scripts manuais de
integração (batem em Mongo/SMTP/Gemini de verdade), não testes automatizados.

## Sandbox (Área de Teste de Desenvolvimento)

A pasta `sandbox/` é uma área de teste de desenvolvimento.

Ela existe para validar experimentos sem acoplar diretamente na pipeline de produção, por exemplo:

- teste de conexão com MongoDB
- teste de Gemini
- teste de envio SMTP (Mailtrap)
- teste de integração do fluxo de lembrete

Scripts atuais no sandbox:

- `sandbox/test_atlas.py`
- `sandbox/test_gemini.py`
- `sandbox/test_email_mailtrap.py`
- `sandbox/check_mongo_coverage.py`
- `sandbox/test_deadline_reminder_integration.py`

Teste de integração de lembrete (sem pipeline de produção):

```powershell
python .\sandbox\test_deadline_reminder_integration.py --source cnpq --step 7
```

Modo real (envia e-mail):

```powershell
python .\sandbox\test_deadline_reminder_integration.py --source cnpq --step 7 --send-email
```

## Boas Práticas

- Não versionar `.env`.
- Não expor credenciais em commits, logs ou README.
- Rotacionar chaves caso alguma seja exposta.

## Como Trocar o Modelo de IA

O pipeline atualmente está integrado ao Google Gemini via SDK `google.genai`.

Para trocar apenas o modelo Gemini, altere a constante `MODEL` em `pipeline/pdf_pipeline/analyzer.py`:

```python
MODEL = "gemini-2.5-pro"
```

Para usar outro provedor/modelo, não basta trocar o nome do modelo. Será necessário:

- instalar o SDK ou biblioteca do novo provedor;
- implementar uma função de chamada específica;
- adaptar autenticação, envio de prompt e parsing da resposta;
- manter uma interface semelhante a `call_gemini` para facilitar manutenção.
