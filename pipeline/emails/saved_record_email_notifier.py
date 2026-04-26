from __future__ import annotations

import json
import os
from html import escape

from dotenv import load_dotenv

from .smtp_email_service import SmtpEmailService
from .send_email_use_case import SendEmailUseCase


class SavedRecordEmailNotifier:
    """Notifica por email quando um registro foi salvo no MongoDB."""
    # Esta classe representa a regra especifica do projeto:
    # depois de salvar no MongoDB, transformar os dados em HTML e enviar para teste.

    def __init__(self, test_recipient: str | None = None) -> None:
        # O destinatario de teste vem do .env para nao ficar fixo no codigo.
        load_dotenv(override=True)
        self.test_recipient = (test_recipient or os.getenv("TEST_EMAIL_TO") or "").strip()
        self._use_case: SendEmailUseCase | None = None

    def is_enabled(self) -> bool:
        # O envio so acontece se houver destinatario configurado.
        return bool(self.test_recipient)

    def notify_saved_record(
        self,
        *,
        source_label: str,
        source_id: str,
        collection_name: str,
        save_status: str,
        pdf_url: str,
        saved_json: dict,
    ) -> None:
        # Se nao houver destinatario, o fluxo simplesmente ignora a notificacao.
        if not self.is_enabled():
            return

        # O caso de uso e criado sob demanda, apenas quando realmente vamos enviar.
        if self._use_case is None:
            self._use_case = SendEmailUseCase(SmtpEmailService())

        # O assunto resume o evento principal: registro salvo e origem do dado.
        subject = (
            f"[IAUPE] Registro salvo no MongoDB ({save_status}) - "
            f"{source_label} ({source_id})"
        )

        # O HTML concentra os campos principais e inclui o JSON salvo para auditoria visual.
        html_body = self._build_saved_record_html(
            source_label=source_label,
            source_id=source_id,
            collection_name=collection_name,
            save_status=save_status,
            pdf_url=pdf_url,
            saved_json=saved_json,
        )

        # Aqui a notificacao sai da regra de negocio e entra no caso de uso generico de email.
        self._use_case.execute(
            {
                "to": self.test_recipient,
                "subject": subject,
                "html": html_body,
            }
        )

    def _build_saved_record_html(
        self,
        *,
        source_label: str,
        source_id: str,
        collection_name: str,
        save_status: str,
        pdf_url: str,
        saved_json: dict,
    ) -> str:
        # Escapa os campos para nao quebrar o HTML caso algum texto tenha caracteres especiais.
        publico_alvo = escape(str(saved_json.get("publico_alvo") or "N/A"))
        data_limite = escape(str(saved_json.get("data_limit_submissao") or "N/A"))
        json_pretty = escape(json.dumps(saved_json, ensure_ascii=False, indent=2))
        safe_url = escape(pdf_url)

        # O corpo HTML apresenta um resumo legivel e, abaixo, o JSON completo salvo no banco.
        return (
            "<html>"
            "<body style='font-family: Arial, sans-serif; color: #1f2937;'>"
            "<h2 style='margin-bottom: 8px;'>Registro salvo no MongoDB</h2>"
            f"<p><b>Fonte:</b> {escape(source_label)} ({escape(source_id)})</p>"
            f"<p><b>Collection:</b> {escape(collection_name)}</p>"
            f"<p><b>Status do save:</b> {escape(save_status)}</p>"
            f"<p><b>URL PDF:</b> <a href='{safe_url}'>{safe_url}</a></p>"
            f"<p><b>Data limite submissao:</b> {data_limite}</p>"
            f"<p><b>Publico-alvo:</b> {publico_alvo}</p>"
            "<h3 style='margin-top: 16px;'>JSON salvo</h3>"
            "<pre style='background:#f3f4f6; padding:12px; border-radius:8px; "
            "white-space:pre-wrap; word-break:break-word;'>"
            f"{json_pretty}"
            "</pre>"
            "</body>"
            "</html>"
        )