import os


def parse_limit(raw_value: str | None) -> int | None:
    raw_limit = (raw_value or "all").strip().lower()
    return None if raw_limit in ("all", "0", "none", "") else int(raw_limit)


LIMIT = parse_limit(os.getenv("PIPELINE_LIMIT"))

SLEEP_ALREADY_EXISTS = int((os.getenv("SLEEP_ALREADY_EXISTS") or "5").strip())
SLEEP_NEW_PROCESS = int((os.getenv("SLEEP_NEW_PROCESS") or "60").strip())
SLEEP_EMPTY_TEXT = int((os.getenv("SLEEP_EMPTY_TEXT") or "5").strip())

MAX_RETRIES_GEMINI = int((os.getenv("MAX_RETRIES_GEMINI") or "3").strip())
