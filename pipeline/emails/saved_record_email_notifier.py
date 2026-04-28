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
        self.test_recipient = (test_recipient or os.getenv("RECIPIENT_EMAIL") or "").strip()
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
        safe_url = escape(pdf_url)
        publico_alvo = escape(str(saved_json.get("publico_alvo") or "N/A"))
        descricao = escape(str(saved_json.get("descricao") or "N/A"))
        data_limite = escape(str(saved_json.get("data_limit_submissao") or "N/A"))
        criterios_publico = self.render_list(saved_json.get("criterios_publico_alvo"))
        criterios_proponente = self.render_list(saved_json.get("criterios_proponente"))
        observacoes = self.render_list(saved_json.get("observacoes"))
        cronograma = self.render_list(saved_json.get("cronograma"))
        areas_interesse = self.render_badges(saved_json.get("areas_interesse"))
        segmentos = self.render_badges(saved_json.get("segmentos"))

        return (
            "<html lang='pt-BR'>"
            "<head>"
            "<meta charset='UTF-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
            "<title>Preview - Novo Edital Identificado</title>"
            "<link href='https://fonts.googleapis.com/css?family=Montserrat:400,600,700&display=swap' rel='stylesheet'>"
            "</head>"
            "<body style=\"margin:0; padding:0; background-color:#dce8f5; font-family:'Montserrat', Arial, sans-serif; color:#1a1a2e;\">"
            "<table width='100%' cellpadding='0' cellspacing='0' border='0' style='background:#dce8f5; padding:32px 16px;'>"
            "<tr><td align='center'>"
            "<table width='620' cellpadding='0' cellspacing='0' border='0' style='max-width:620px; width:100%;'>"
            "<tr><td style='background:#c0392b; height:5px; border-radius:8px 8px 0 0;'></td></tr>"
            "<tr><td style='background:linear-gradient(135deg, #1a3a6b 0%, #2a5298 100%); padding:28px 36px 24px;'>"
            "<table width='100%'><tr><td>"
            "<p style='margin:0 0 2px; font-size:10px; letter-spacing:3px; text-transform:uppercase; color:#a8c4e8; font-weight:600;'>Plataforma de Monitoramento de Editais</p>"
            "<h1 style='margin:0; font-family:Montserrat,Arial,sans-serif; font-size:22px; font-weight:600; color:#ffffff;'>Novo Edital Identificado</h1>"
            "</td><td align='right'><span style='display:inline-block; background:#c0392b; color:#fff; font-size:10px; font-weight:700; letter-spacing:2px; text-transform:uppercase; padding:5px 14px; border-radius:3px;'>Novo</span></td></tr></table>"
            "</td></tr>"
            "<tr><td style='background:#2a5298; padding:14px 36px; border-bottom:2px solid #c0392b;'>"
            "<table width='100%'><tr><td><span style='font-size:13px; color:#a8c4e8;'>Instituição: </span><span style='font-size:14px; font-weight:700; color:#fff;'>" + escape(source_label) + "</span></td><td align='right'><span style='font-family:Courier New,monospace; font-size:11px; color:#a8c4e8; background:#1a3a6b; padding:4px 10px; border-radius:3px;'>Ref: " + escape(source_id) + "</span></td></tr></table>"
            "</td></tr>"
            "<tr><td style='background:#ffffff; padding:0;'>"
            "<table width='100%' style='border-bottom:1px solid #dce8f5;'><tr>"
            "<td style='width:50%; padding:24px 36px 20px; border-right:1px solid #dce8f5;'><p style='margin:0 0 4px; font-size:10px; letter-spacing:2.5px; text-transform:uppercase; color:#7a90aa; font-weight:600;'>Prazo final de submissão</p><p style='margin:0; font-family:Montserrat,Arial,sans-serif; font-size:22px; font-weight:600; color:#c0392b;'>" + data_limite + "</p></td>"
            "<td style='width:50%; padding:24px 36px 20px;'><p style='margin:0 0 4px; font-size:10px; letter-spacing:2.5px; text-transform:uppercase; color:#7a90aa; font-weight:600;'>Documento oficial</p><a href='" + safe_url + "' style='font-size:14px; font-weight:700; color:#2a5298; text-decoration:none;'>→ Acessar edital em PDF</a></td>"
            "</tr></table>"
            "<div style='padding:20px 36px; border-bottom:1px solid #eaf1fb;'><p style='margin:0 0 10px; font-size:10px; letter-spacing:2.5px; text-transform:uppercase; color:#2a5298; font-weight:700;'>Público-alvo</p><p style='margin:0; font-family:Montserrat,Arial,sans-serif; font-size:15px; line-height:1.75; color:#2d3748;'>" + publico_alvo + "</p></div>"
            "<div style='padding:20px 36px; border-bottom:1px solid #eaf1fb;'><p style='margin:0 0 10px; font-size:10px; letter-spacing:2.5px; text-transform:uppercase; color:#2a5298; font-weight:700;'>Resumo do Edital</p><p style='margin:0; font-family:Montserrat,Arial,sans-serif; font-size:15px; line-height:1.75; color:#2d3748;'>" + descricao + "</p></div>"
            "<div style='padding:0 36px; border-bottom:1px solid #eaf1fb;'><table width='100%'><tr valign='top'><td style='width:50%; padding:20px 16px 20px 0; border-right:1px solid #eaf1fb;'><p style='margin:0 0 10px; font-size:10px; letter-spacing:2.5px; text-transform:uppercase; color:#2a5298; font-weight:700;'>Áreas de interesse</p>" + areas_interesse + "</td><td style='width:50%; padding:20px 0 20px 16px;'><p style='margin:0 0 10px; font-size:10px; letter-spacing:2.5px; text-transform:uppercase; color:#2a5298; font-weight:700;'>Segmentos</p>" + segmentos + "</td></tr></table></div>"
            "<div style='padding:20px 36px; border-bottom:1px solid #eaf1fb;'><p style='margin:0 0 10px; font-size:10px; letter-spacing:2.5px; text-transform:uppercase; color:#2a5298; font-weight:700;'>Quem pode submeter</p>" + criterios_proponente + "</div>"
            "<div style='padding:20px 36px; border-bottom:1px solid #eaf1fb;'><p style='margin:0 0 10px; font-size:10px; letter-spacing:2.5px; text-transform:uppercase; color:#2a5298; font-weight:700;'>Cronograma</p>" + cronograma + "</div>"
            "</td></tr>"
            "<tr><td style='background:#eaf1fb; padding:28px 36px; text-align:center; border-top:2px solid #2a5298;'><a href='" + safe_url + "' style='display:inline-block; background:#2a5298; color:#fff; font-size:13px; font-weight:700; letter-spacing:1px; text-transform:uppercase; text-decoration:none; padding:13px 40px; border-radius:3px;'>Acessar Edital Completo</a></td></tr>"
            "<tr><td style='background:#1a3a6b; border-radius:0 0 8px 8px; padding:20px 36px; text-align:center;'><p style='margin:0; font-size:11px; color:#7a9cc8; line-height:1.7;'>Este e-mail foi gerado automaticamente pela plataforma de monitoramento de editais.<br>Você está recebendo esta mensagem porque está cadastrado para receber alertas de oportunidades.</p></td></tr>"
            "</table>"
            "</td></tr>"
            "</table>"
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