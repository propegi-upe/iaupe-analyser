"""
Testes das travas de volume do envio de notificacoes por area/segmento
(pipeline/orchestration/docente_notification_service.py).

select_recipients e pura (sem I/O). notify_docentes_for_edital chama envio de
verdade quando dry_run=False, entao usamos um notifier fake simples (sem
unittest.mock) em vez de bater em SMTP real.
"""

from __future__ import annotations

from pipeline.orchestration.docente_match import DocenteMatch
from pipeline.orchestration.docente_notification_service import (
    notify_docentes_for_edital,
    select_recipients,
)


def _match(email: str) -> DocenteMatch:
    return DocenteMatch(email=email, areas=["Saude"], segmentos=[])


class FakeNotifier:
    """Substitui SavedRecordEmailNotifier: nao faz I/O, so registra a chamada."""

    def __init__(self, delivered: list[str] | None = None):
        self.delivered = delivered if delivered is not None else []
        self.calls: list[list[str]] = []

    def notify_saved_record_bcc(self, *, recipients, **_kwargs):
        self.calls.append(list(recipients))
        return self.delivered if self.delivered else list(recipients)


def test_select_recipients_descarta_quem_ja_foi_avisado():
    matches = [_match("a@upe.br"), _match("b@upe.br")]

    selecionados = select_recipients(matches, already_notified={"a@upe.br"})

    assert [m.email for m in selecionados] == ["b@upe.br"]


def test_select_recipients_respeita_limite_por_docente():
    matches = [_match("a@upe.br")]

    selecionados = select_recipients(
        matches, sent_per_docente={"a@upe.br": 3}, max_por_docente=3
    )

    assert selecionados == []


def test_select_recipients_corta_pela_cota_restante():
    matches = [_match("a@upe.br"), _match("b@upe.br"), _match("c@upe.br")]

    selecionados = select_recipients(matches, remaining_quota=2)

    assert [m.email for m in selecionados] == ["a@upe.br", "b@upe.br"]


def test_notify_docentes_dry_run_nao_chama_notifier_e_atualiza_contador():
    docentes = [{"email": "a@upe.br", "areas_interesse": ["Saude"], "segmentos": []}]
    notifier = FakeNotifier()
    sent_per_docente: dict[str, int] = {}

    enviados = notify_docentes_for_edital(
        notifier=notifier,
        docentes=docentes,
        source_id="facepe",
        source_label="FACEPE",
        pdf_url="https://exemplo.org/edital.pdf",
        resultado={"areas_interesse": ["Saude"], "segmentos": []},
        sent_per_docente=sent_per_docente,
        dry_run=True,
    )

    assert enviados == ["a@upe.br"]
    assert notifier.calls == []  # dry-run nao dispara envio real
    assert sent_per_docente == {"a@upe.br": 1}


def test_notify_docentes_envia_de_verdade_quando_nao_e_dry_run():
    docentes = [{"email": "a@upe.br", "areas_interesse": ["Saude"], "segmentos": []}]
    notifier = FakeNotifier(delivered=["a@upe.br"])
    sent_per_docente: dict[str, int] = {}

    enviados = notify_docentes_for_edital(
        notifier=notifier,
        docentes=docentes,
        source_id="facepe",
        source_label="FACEPE",
        pdf_url="https://exemplo.org/edital.pdf",
        resultado={"areas_interesse": ["Saude"], "segmentos": []},
        sent_per_docente=sent_per_docente,
        dry_run=False,
    )

    assert enviados == ["a@upe.br"]
    assert notifier.calls == [["a@upe.br"]]


def test_notify_docentes_falha_no_envio_nao_marca_ninguem():
    docentes = [{"email": "a@upe.br", "areas_interesse": ["Saude"], "segmentos": []}]

    class BrokenNotifier:
        def notify_saved_record_bcc(self, *_args, **_kwargs):
            raise RuntimeError("SMTP indisponivel")

    sent_per_docente: dict[str, int] = {}

    enviados = notify_docentes_for_edital(
        notifier=BrokenNotifier(),
        docentes=docentes,
        source_id="facepe",
        source_label="FACEPE",
        pdf_url="https://exemplo.org/edital.pdf",
        resultado={"areas_interesse": ["Saude"], "segmentos": []},
        sent_per_docente=sent_per_docente,
        dry_run=False,
    )

    assert enviados == []
    assert sent_per_docente == {}
