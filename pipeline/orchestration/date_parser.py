from datetime import datetime, timezone


def parse_data_limit_submissao(raw_value: str | None) -> datetime | None:
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
