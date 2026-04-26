from __future__ import annotations

from typing import Protocol

from .email import Email


# Este contrato desacopla o caso de uso da tecnologia de envio.
# Assim, o use case conhece apenas a operacao "send", sem depender de SMTP diretamente.
class EmailsService(Protocol):
    """Contrato para implementacoes de envio de email."""
    def send(self, email: Email) -> None:
        ...
