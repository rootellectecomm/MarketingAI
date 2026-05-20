from __future__ import annotations

import re

PHONE_PATTERN = re.compile(r"(?:\+91|91|0)?[6-9]\d{9}")


def extract_phone(text: str) -> str | None:
    match = PHONE_PATTERN.search(text.replace(" ", "").replace("-", ""))
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(0))
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    if len(digits) == 13 and digits.startswith("91"):
        return f"+{digits}"
    if text.strip().startswith("+") and len(digits) >= 10:
        return f"+{digits}"
    return None
