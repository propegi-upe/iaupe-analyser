from __future__ import annotations

from .email import Email
from .emails_service import EmailsService


# caso de uso: orquestra o envio.
# o use case:
# 1) cria/valida a entidade Email
# 2) delega o envio para um EmailsService
class SendEmailUseCase:
    """Caso de uso de envio de email desacoplado da implementacao SMTP."""
    def __init__(self, emails_service: EmailsService) -> None:
        # injecao de dependencia pelo contrato (protocol)
        self.emails_service = emails_service

    def execute(self, data: dict) -> None:
        """Valida payload de email e delega o envio ao servico injetado."""
        # valida e cria o email a partir dos dados recebidos
        email = Email.create(data)

        # envia usando a implementacao injetada
        self.emails_service.send(email)
