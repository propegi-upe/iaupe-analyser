from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    text: str | None = None
    html: str | None = None

    @staticmethod
    def create(data: dict) -> "Email":
        to = (data.get("to") or "").strip()
        subject = (data.get("subject") or "").strip()
        text = data.get("text")
        html = data.get("html")

        if not to:
            raise ValueError("Email.to e obrigatorio")
        if not subject:
            raise ValueError("Email.subject e obrigatorio")
        if not (text or html):
            raise ValueError("Informe ao menos text ou html")

        return Email(to=to, subject=subject, text=text, html=html)
