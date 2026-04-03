from dotenv import load_dotenv
import sys
from pathlib import Path

# garante que a raiz do projeto esteja no pythonpath para importar "pipeline"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.emails.gmail_smtp_email_service import GmailSmtpEmailService
from pipeline.emails.send_email_use_case import SendEmailUseCase


# teste simples de envio para o sandbox do mailtrap
# o email nao vai para a caixa real; ele aparece na inbox de testes do mailtrap

def main() -> None:
    load_dotenv(override=True)

    use_case = SendEmailUseCase(GmailSmtpEmailService())

    use_case.execute(
        {
            "to": "to@example.com",
            "subject": "Hi Mailtrap",
            "text": "This is a test e-mail message.",
        }
    )

    print("email de teste enviado para o mailtrap")


if __name__ == "__main__":
    main()
