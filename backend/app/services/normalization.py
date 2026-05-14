from __future__ import annotations

import html
import re
import unicodedata


def normalize_comment_text(text: str) -> str:
    value = html.unescape(text or "")
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"@\w+", " ", value)
    value = re.sub(r"#", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def detect_language(text: str) -> str:
    # V1 is English-only. Keep a hook here so multilingual support can be enabled later.
    return "en"

