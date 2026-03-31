from __future__ import annotations

import os
import smtplib
from dotenv import load_dotenv

from .email import Email


class GmailSmtpEmailService:
    def __init__(self) -> None:
        load_dotenv(override=True)

        self.host = (os.getenv("SMTP_HOST") or "smtp.gmail.com").strip()
        self.port = int((os.getenv("SMTP_PORT") or "587").strip())
        self.user = (os.getenv("SMTP_USER") or "").strip()
        self.password = (os.getenv("SMTP_PASS") or "").strip()
        self.default_from = (os.getenv("DEFAULT_EMAIL_FROM") or self.user).strip()

        if not self.user:
            raise ValueError("Defina SMTP_USER no .env")
        if not self.password:
            raise ValueError("Defina SMTP_PASS no .env (senha de app do Gmail)")

    def send(self, email: Email) -> None:
        body_text = (email.text or "").strip()
        body_html = (email.html or "").strip()
        body = body_html if body_html else body_text
        content_type = "text/html" if body_html else "text/plain"

        if not body:
            raise ValueError("Informe text ou html para envio")

        message = "\r\n".join([
            f"From: {self.default_from}",
            f"To: {email.to}",
            f"Subject: {email.subject}",
            "MIME-Version: 1.0",
            f"Content-Type: {content_type}; charset=utf-8",
            "",
            body,
        ])

        with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(self.user, self.password)
            smtp.sendmail(self.default_from, [email.to], message.encode("utf-8"))
