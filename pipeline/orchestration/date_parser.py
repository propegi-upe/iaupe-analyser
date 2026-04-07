from datetime import datetime, timezone


def parse_data_limit_submissao(raw_value: str | None) -> datetime | None:
    """
    Converte a data limite de submissao para datetime em UTC.

    Aceita prioritariamente YYYY-MM-DD e, em fallback, DD/MM/YYYY.
    Retorna None quando nao houver valor valido.
    """
    raw = (raw_value or "").strip()
    if not raw:
        return None

    # formato esperado da IA: yyyy-mm-dd
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        # fallback defensivo para dd/mm/yyyy
        try:
            parsed = datetime.strptime(raw, "%d/%m/%Y")
        except ValueError:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed
