import re

SOURCE_KEY = "cnpq"
SOURCE_LABEL = "CNPq"
BASE_URL = "https://www.gov.br/cnpq/pt-br/chamadas/abertas-para-submissao"

REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}
DATE_REGEX = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
# "Inscrições: 26/10/2026 a 08/12/2026" - captura a data inicial.
INSCRIPTION_REGEX = re.compile(r"Inscri\w+\s*:\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE)
URL_REGEX = re.compile(r"https?://[^\s'\"<>]+", re.IGNORECASE)
