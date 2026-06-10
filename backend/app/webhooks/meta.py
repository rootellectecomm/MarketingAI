from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Literal

SignatureStatus = Literal["valid", "invalid", "unknown"]


def verify_meta_signature(raw_body: bytes, signature_header: str | None, app_secret: str) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    digest = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature_header)


def evaluate_webhook_signature(
    raw_body: bytes,
    signature_header: str | None,
    app_secret: str | None,
    *,
    unknown_when_secret_missing: bool = False,
) -> SignatureStatus:
    secret = (app_secret or "").strip()
    if not secret or secret.startswith("replace-") or secret.startswith("change-me"):
        return "unknown" if unknown_when_secret_missing else "invalid"
    if not signature_header or not signature_header.startswith("sha256="):
        return "invalid"
    if verify_meta_signature(raw_body, signature_header, secret):
        return "valid"
    return "invalid"


def signature_status_to_bool(status: SignatureStatus) -> bool | None:
    if status == "valid":
        return True
    if status == "invalid":
        return False
    return None


def webhook_fingerprint(payload: dict[str, Any]) -> str:
    stable = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()
