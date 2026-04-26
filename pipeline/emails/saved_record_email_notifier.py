from __future__ import annotations

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

    def build_saved_record_html(
        self,
        *,
        source_label: str,
        source_id: str,
        collection_name: str,
        save_status: str,
        pdf_url: str,
        saved_json: dict,
    ) -> str:
        # Monta um email legivel para humanos, sem despejar o JSON bruto no corpo.
        safe_url = escape(pdf_url)
        publico_alvo = escape(str(saved_json.get("publico_alvo") or "N/A"))
        descricao = escape(str(saved_json.get("descricao") or "N/A"))
        data_limite = escape(str(saved_json.get("data_limit_submissao") or "N/A"))
        criterios_publico = self._render_list(saved_json.get("criterios_publico_alvo"))
        criterios_proponente = self._render_list(saved_json.get("criterios_proponente"))
        observacoes = self._render_list(saved_json.get("observacoes"))
        cronograma = self._render_list(saved_json.get("cronograma"))
        areas_interesse = self._render_badges(saved_json.get("areas_interesse"))
        segmentos = self._render_badges(saved_json.get("segmentos"))

        return (
            "<html>"
            "<body style='margin:0; padding:24px; background:#f4f7fb; font-family:Arial, sans-serif; color:#1f2937;'>"
            "<div style='max-width:820px; margin:0 auto; background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; overflow:hidden;'>"
            "<div style='background:#0f172a; color:#ffffff; padding:20px 24px;'>"
            "<h1 style='margin:0; font-size:24px;'>Registro salvo no MongoDB</h1>"
            f"<p style='margin:8px 0 0; font-size:14px; opacity:0.9;'>{escape(source_label)} ({escape(source_id)})</p>"
            "</div>"
            "<div style='padding:24px;'>"
            "<table style='width:100%; border-collapse:collapse; margin-bottom:24px;'>"
            "<tr><td style='padding:8px 0; width:180px;'><b>Collection</b></td>"
            f"<td style='padding:8px 0;'>{escape(collection_name)}</td></tr>"
            "<tr><td style='padding:8px 0;'><b>Status do save</b></td>"
            f"<td style='padding:8px 0;'>{escape(save_status)}</td></tr>"
            "<tr><td style='padding:8px 0;'><b>Data limite</b></td>"
            f"<td style='padding:8px 0;'>{data_limite}</td></tr>"
            "<tr><td style='padding:8px 0;'><b>URL do PDF</b></td>"
            f"<td style='padding:8px 0;'><a href='{safe_url}' style='color:#2563eb; text-decoration:none;'>Abrir edital</a></td></tr>"
            "</table>"
            "<h2 style='font-size:18px; margin:0 0 8px;'>Publico-alvo</h2>"
            f"<p style='margin:0 0 20px; line-height:1.6;'>{publico_alvo}</p>"
            "<h2 style='font-size:18px; margin:0 0 8px;'>Descricao</h2>"
            f"<p style='margin:0 0 20px; line-height:1.6;'>{descricao}</p>"
            "<h2 style='font-size:18px; margin:0 0 8px;'>Areas de interesse</h2>"
            f"<div style='margin:0 0 20px;'>{areas_interesse}</div>"
            "<h2 style='font-size:18px; margin:0 0 8px;'>Segmentos</h2>"
            f"<div style='margin:0 0 20px;'>{segmentos}</div>"
            "<h2 style='font-size:18px; margin:0 0 8px;'>Criterios do publico-alvo</h2>"
            f"{criterios_publico}"
            "<h2 style='font-size:18px; margin:20px 0 8px;'>Criterios do proponente</h2>"
            f"{criterios_proponente}"
            "<h2 style='font-size:18px; margin:20px 0 8px;'>Observacoes</h2>"
            f"{observacoes}"
            "<h2 style='font-size:18px; margin:20px 0 8px;'>Cronograma</h2>"
            f"{cronograma}"
            "</div>"
            "</div>"
            "</body>"
            "</html>"
        )

    def render_list(self, items: list | None) -> str:
        values = [escape(str(item).strip()) for item in (items or []) if str(item).strip()]
        if not values:
            return "<p style='color:#6b7280;'>Nao informado.</p>"

        rows = "".join(
            f"<li style='margin:0 0 8px; line-height:1.5;'>{value}</li>"
            for value in values
        )
        return f"<ul style='margin:0; padding-left:20px;'>{rows}</ul>"

    def render_badges(self, items: list | None) -> str:
        values = [escape(str(item).strip()) for item in (items or []) if str(item).strip()]
        if not values:
            return "<p style='color:#6b7280;'>Nao informado.</p>"

        return "".join(
            "<span style='display:inline-block; margin:0 8px 8px 0; padding:6px 10px; "
            "background:#e0f2fe; color:#075985; border-radius:999px; font-size:13px;'>"
            f"{value}</span>"
            for value in values
        )