from __future__ import annotations

from dataclasses import dataclass

# Esta entidade representa um email pronto para envio.
# A ideia aqui e centralizar a validacao minima antes de chegar no servico SMTP.
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
        # A pipeline monta payloads simples em dict.
        # Este metodo converte esse payload para um objeto de dominio validado.
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

        # Se passou pela validacao, o restante do fluxo trabalha com um objeto consistente.
        return Email(to=to, subject=subject, text=text, html=html)
