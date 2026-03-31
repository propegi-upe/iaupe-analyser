from __future__ import annotations

from .email import Email
from .emails_service import EmailsService


class SendEmailUseCase:
    def __init__(self, emails_service: EmailsService) -> None:
        self.emails_service = emails_service

    def execute(self, data: dict) -> None:
        email = Email.create(data)
        self.emails_service.send(email)
