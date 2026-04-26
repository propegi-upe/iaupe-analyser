from __future__ import annotations

from .email import Email
from .emails_service import EmailsService


# Este caso de uso concentra a regra de aplicacao do envio.
# Ele nao sabe nada sobre SMTP; apenas valida o payload e delega ao servico injetado.
class SendEmailUseCase:
    """Caso de uso de envio de email desacoplado da implementacao SMTP."""
    def __init__(self, emails_service: EmailsService) -> None:
        # Injecao de dependencia permite trocar o mecanismo de envio sem mexer no fluxo.
        self.emails_service = emails_service

    def execute(self, data: dict) -> None:
        """Valida payload de email e delega o envio ao servico injetado."""
        # Primeiro, garante que o payload recebido e um email valido.
        email = Email.create(data)

        # Depois, envia usando a implementacao concreta configurada na aplicacao.
        self.emails_service.send(email)
