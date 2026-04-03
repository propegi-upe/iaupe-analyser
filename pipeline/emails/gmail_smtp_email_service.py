from __future__ import annotations

import os
import smtplib
from dotenv import load_dotenv

from .email import Email


# usa tls + login e envia a mensagem.
# configuracao vem do .env:
# - smtp_host, smtp_port
# - smtp_user, smtp_pass
# - default_email_from (opcional)

class GmailSmtpEmailService:
    def __init__(self) -> None:
        # carrega variaveis do .env para nao hardcodear credenciais
        load_dotenv(override=True)

        # servidor smtp (gmail por padrao)
        self.host = (os.getenv("SMTP_HOST") or "smtp.gmail.com").strip()
        self.port = int((os.getenv("SMTP_PORT") or "587").strip())

        # credenciais
        self.user = (os.getenv("SMTP_USER") or "").strip()
        self.password = (os.getenv("SMTP_PASS") or "").strip()

        # remetente padrao
        self.default_from = (os.getenv("DEFAULT_EMAIL_FROM") or self.user).strip()

        if not self.user:
            raise ValueError("Defina SMTP_USER no .env")
        if not self.password:
            raise ValueError("Defina SMTP_PASS no .env")

    def send(self, email: Email) -> None:
        # escolhe corpo do email:
        # - se houver html, ele tem prioridade
        # - caso contrario usa text
        body_text = (email.text or "").strip()
        body_html = (email.html or "").strip()
        body = body_html if body_html else body_text
        content_type = "text/html" if body_html else "text/plain"

        if not body:
            raise ValueError("Informe text ou html para envio")

        # monta uma mensagem mime simples com headers + corpo.
        # obs: isso e suficiente para o objetivo do projeto (envio basico).
        message = "\r\n".join([
            f"From: {self.default_from}",
            f"To: {email.to}",
            f"Subject: {email.subject}",
            "MIME-Version: 1.0",
            f"Content-Type: {content_type}; charset=utf-8",
            "",
            body,
        ])

        # fluxo smtp:
        # 1) conecta
        # 2) starttls (criptografa)
        # 3) login
        # 4) sendmail
        with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(self.user, self.password)
            smtp.sendmail(self.default_from, [email.to], message.encode("utf-8"))
