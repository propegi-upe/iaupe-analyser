from __future__ import annotations

from dataclasses import dataclass

# tudo que for enviar deve virar um objeto Email validado pelo visto.
@dataclass(frozen=True)
class Email:
    """Entidade de email com validacao minima para envio seguro."""
    to: str
    subject: str
    text: str | None = None
    html: str | None = None

    @staticmethod
    def create(data: dict) -> "Email":
        """Fabrica de Email a partir de dict com validacao de campos obrigatorios."""
        # factory que transforma um dict em Email e valida as regras minimas.
        # regras:
        # - to e obrigatorio
        # - subject e obrigatorio
        # - precisa ter pelo menos text ou html
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
