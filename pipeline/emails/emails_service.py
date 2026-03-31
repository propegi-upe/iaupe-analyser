from __future__ import annotations

from typing import Protocol

from .email import Email


class EmailsService(Protocol):
    def send(self, email: Email) -> None:
        ...
