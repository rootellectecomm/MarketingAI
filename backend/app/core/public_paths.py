from __future__ import annotations

PUBLIC_WEBHOOK_PREFIXES = ("/webhooks/meta/",)
PUBLIC_WEBHOOK_EXACT = {"/webhook"}


def is_public_webhook_path(path: str) -> bool:
    """Meta webhook delivery must not require dashboard JWT auth."""
    if path in PUBLIC_WEBHOOK_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_WEBHOOK_PREFIXES)
