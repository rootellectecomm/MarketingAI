from __future__ import annotations

from fastapi import HTTPException
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings


def verify_meta_hub_challenge(
    hub_mode: str | None,
    hub_verify_token: str | None,
    hub_challenge: str | None,
) -> PlainTextResponse:
    """Meta webhook subscription verification — body must be plain text challenge only."""
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.meta_verify_token and hub_challenge:
        return PlainTextResponse(content=str(hub_challenge))
    raise HTTPException(status_code=403, detail="Verification failed")

