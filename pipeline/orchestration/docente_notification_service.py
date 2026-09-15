from __future__ import annotations

import logging
import os

from db.match_notifications import mark_match_emails_sent
from emails.saved_record_email_notifier import SavedRecordEmailNotifier

from .docente_match import DocenteMatch, match_docentes
from .source_registry import SOURCE_REGISTRY

logger = logging.getLogger(__name__)

# Motor de notificacao por area/segmento: cruza, seleciona (aplicando as travas
# de volume) e envia. Usado tanto pelo fluxo automatico (pipeline_runner.py,
# um edital por vez, assim que e salvo) quanto pelo backfill avulso
# (new_edital_notify_runner.py, varios editais de uma vez).

# Travas de volume. O envio e feito em copia oculta (um e-mail por edital, com
# todos os docentes que casam em BCC), entao a contagem de MENSAGENS e baixa; o
# que estas travas limitam e a quantidade de DESTINATARIOS por execucao. Sem
# elas, uma varredura de todos os editais com prazo aberto colocaria a mesma
# pessoa em dezenas de listas de BCC - parece spam e queima a reputacao da conta.
DEFAULT_MAX_POR_DOCENTE = 3
DEFAULT_MAX_EMAILS = 300


def notificacao_docentes_habilitada() -> bool:
    """
    Interruptor de emergencia da notificacao por area/segmento.

    Ligada por padrao. Para desligar sem mexer no codigo (ex.: suspeita de envio
    indevido, manutencao na base de docentes), basta definir NOTIFY_DOCENTES=0
    no .env ou nos secrets do GitHub - a pipeline continua coletando e salvando
    editais normalmente, so para de avisar os docentes.
    """
    raw = (os.getenv("NOTIFY_DOCENTES") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off", "disabled"}


def resolve_source_label(fonte: str) -> str:
    """Label amigavel da fonte (ex.: 'facepe' -> 'FACEPE'), usado no assunto."""
    source = SOURCE_REGISTRY.get((fonte or "").strip().lower())
    if source:
        return str(source["label"])
    return (fonte or "").upper() or "Fonte desconhecida"


def select_recipients(
    matches: list[DocenteMatch],
    *,
    already_notified: set[str] | None = None,
    sent_per_docente: dict[str, int] | None = None,
    max_por_docente: int = DEFAULT_MAX_POR_DOCENTE,
    remaining_quota: int | None = None,
) -> list[DocenteMatch]:
    """
    Decide QUEM recebe, sem enviar nada (funcao pura, facil de testar).

    Descarta, nesta ordem: quem ja foi avisado deste edital (`already_notified`,
    lido do banco), quem ja bateu o limite de e-mails desta execucao
    (`sent_per_docente`) e o que exceder a cota restante da execucao.

    Quem fica de fora nao e marcado como enviado em lugar nenhum, entao entra
    naturalmente na proxima execucao.
    """
    ja_avisados = already_notified or set()
    contador = sent_per_docente or {}
    selecionados: list[DocenteMatch] = []

    for match in matches:
        if match.email in ja_avisados:
            continue
        if contador.get(match.email, 0) >= max_por_docente:
            continue
        if remaining_quota is not None and len(selecionados) >= remaining_quota:
            break
        selecionados.append(match)

    return selecionados


def send_to_recipients(
    *,
    notifier: SavedRecordEmailNotifier,
    recipients: list[DocenteMatch],
    source_id: str,
    source_label: str,
    pdf_url: str,
    resultado: dict,
) -> list[str]:
    """
    Envia UM e-mail com todos os destinatarios em copia oculta e marca no banco
    quem recebeu. Devolve a lista de e-mails que sairam.

    Reaproveita o e-mail de edital novo que ja existe (SavedRecordEmailNotifier):
    o docente recebe exatamente a mesma mensagem que o endereco institucional.
    O envio e fatiado em blocos pelo SmtpEmailService; um bloco que falha e
    pulado (seus docentes nao entram no retorno e nao sao marcados, entao
    reentram numa proxima execucao).
    """
    emails = [match.email for match in recipients]

    try:
        delivered = notifier.notify_saved_record_bcc(
            recipients=emails,
            source_label=source_label,
            source_id=source_id,
            pdf_url=pdf_url,
            saved_json=resultado,
        )
    except Exception as exc:
        logger.error("Falha ao notificar docentes sobre %s: %s", pdf_url, exc, exc_info=True)
        return []

    if delivered:
        mark_match_emails_sent(url_pdf=pdf_url, emails=delivered)

    return delivered


def notify_docentes_for_edital(
    *,
    notifier: SavedRecordEmailNotifier,
    docentes: list[dict],
    source_id: str,
    source_label: str,
    pdf_url: str,
    resultado: dict,
    sent_per_docente: dict[str, int],
    already_notified: set[str] | None = None,
    max_por_docente: int = DEFAULT_MAX_POR_DOCENTE,
    remaining_quota: int | None = None,
    dry_run: bool = False,
) -> list[str]:
    """
    Cruza, seleciona e notifica os docentes de UM edital. Devolve quem recebeu.

    `sent_per_docente` e o contador da execucao inteira e e ATUALIZADO aqui - e
    o que garante o limite por pessoa quando varios editais entram de uma vez.

    Com `dry_run=True` percorre exatamente o mesmo caminho, mas nao envia nem
    marca nada: a simulacao mostra o que aconteceria de verdade, e nao uma conta
    paralela que poderia divergir do envio real.
    """
    resultado = resultado or {}

    # PASSO 1-3 (o CORACAO do algoritmo, quem casa) acontecem aqui dentro -
    # ver orchestration/docente_match.py::match_docentes para a comparacao
    # area/segmento em si.
    matches = match_docentes(
        docentes,
        resultado.get("areas_interesse"),
        resultado.get("segmentos"),
    )

    # PASSO 4 - das pessoas que casaram, aplica as travas de seguranca (quem ja
    # foi avisado, limite por pessoa, limite total) - ver select_recipients().
    recipients = select_recipients(
        matches,
        already_notified=already_notified,
        sent_per_docente=sent_per_docente,
        max_por_docente=max_por_docente,
        remaining_quota=remaining_quota,
    )
    if not recipients:
        return []

    if dry_run:
        enviados = [match.email for match in recipients]
    else:
        enviados = send_to_recipients(
            notifier=notifier,
            recipients=recipients,
            source_id=source_id,
            source_label=source_label,
            pdf_url=pdf_url,
            resultado=resultado,
        )

    for email in enviados:
        sent_per_docente[email] = sent_per_docente.get(email, 0) + 1

    return enviados
