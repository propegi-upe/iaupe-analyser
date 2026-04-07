from __future__ import annotations

from typing import Protocol

from .email import Email


class EmailsService(Protocol):
    """Contrato para implementacoes de envio de email."""
    def send(self, email: Email) -> None:
        ...
