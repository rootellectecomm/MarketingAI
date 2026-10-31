"""Inbound order events from rootellect.com and the scheduled dispatch trigger."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.init_db import ensure_schema
from app.database.session import get_session
from app.services.provider_factory import get_whatsapp_provider
from app.services.whatsapp_orders import EventValidationError, WhatsAppOrderService
from app.services.whatsapp_template_sync import sync_templates

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["rootellect commerce"])

MAX_CLOCK_SKEW_SECONDS = 300
MAX_BODY_BYTES = 64_000


def compute_signature(secret: str, timestamp: str, raw_body: bytes) -> str:
    message = timestamp.encode() + b"." + raw_body
    return "sha256=" + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def verify_rootellect_signature(
    secret: str | None, timestamp: str | None, signature: str | None, raw_body: bytes, now: float | None = None
) -> bool:
    if not secret or not timestamp or not signature:
        return False
    try:
        sent_at = int(timestamp)
    except ValueError:
        return False
    if abs((now or time.time()) - sent_at) > MAX_CLOCK_SKEW_SECONDS:
        return False
    return hmac.compare_digest(compute_signature(secret, timestamp, raw_body), signature)


@router.post("/webhooks/rootellect/events")
async def receive_rootellect_event(request: Request, session: AsyncSession = Depends(get_session)) -> dict:
    settings = get_settings()
    await ensure_schema()
    raw_body = await request.body()
    if len(raw_body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large")
    if not settings.rootellect_events_secret:
        logger.error("rootellect_events_secret_missing")
        raise HTTPException(status_code=503, detail="Order events are not configured")
    if not verify_rootellect_signature(
        settings.rootellect_events_secret,
        request.headers.get("x-rootellect-timestamp"),
        request.headers.get("x-rootellect-signature"),
        raw_body,
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        event = json.loads(raw_body.decode() or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="Event must be an object")

    try:
        result = await WhatsAppOrderService(settings).handle_event(session, event)
    except EventValidationError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await session.commit()
    logger.info("rootellect_event_processed", type=event.get("type"), event_id=event.get("event_id"), **result.as_dict())
    return {"ok": True, **result.as_dict()}


async def _cron_authorized(request: Request) -> bool:
    """Accept either the cron bearer secret, or a request signed like an order event.

    The signed form lets rootellect.com's existing shipping cron act as the
    heartbeat without sharing a second secret.
    """
    settings = get_settings()
    supplied = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
    supplied = supplied or (request.headers.get("x-cron-secret") or "").strip()
    if settings.cron_secret and supplied and hmac.compare_digest(supplied, settings.cron_secret):
        return True
    if request.method == "POST" and request.headers.get("x-rootellect-signature"):
        return verify_rootellect_signature(
            settings.rootellect_events_secret,
            request.headers.get("x-rootellect-timestamp"),
            request.headers.get("x-rootellect-signature"),
            await request.body(),
        )
    return False


@router.post("/webhooks/cron/whatsapp-templates")
async def sync_whatsapp_templates(request: Request, session: AsyncSession = Depends(get_session)) -> dict:
    """Submit missing order templates to Meta and report approval status.

    Body: ``{"submit": true}`` to create missing templates, ``false`` to only report.
    Uses the WhatsApp credentials the backend already sends with.
    """
    if not await _cron_authorized(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    settings = get_settings()
    if not settings.whatsapp_business_account_id:
        raise HTTPException(status_code=400, detail="Set WHATSAPP_BUSINESS_ACCOUNT_ID (the WhatsApp Business Account ID)")
    try:
        options = json.loads((await request.body()).decode() or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        options = {}
    await ensure_schema()
    provider = await get_whatsapp_provider(session)
    token = getattr(provider, "access_token", None)
    if not token:
        raise HTTPException(status_code=400, detail="No WhatsApp access token configured")
    try:
        templates = await sync_templates(
            settings, token, settings.whatsapp_business_account_id, submit=bool(options.get("submit", True))
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"ok": True, "templates": templates}


@router.api_route("/webhooks/cron/whatsapp-dispatch", methods=["GET", "POST"])
async def dispatch_whatsapp_notifications(request: Request, session: AsyncSession = Depends(get_session)) -> dict:
    """Send due scheduled WhatsApp notifications. Called by a scheduler or rootellect.com's cron."""
    if not await _cron_authorized(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    await ensure_schema()
    counts = await WhatsAppOrderService().dispatch_due(session, limit=40)
    await session.commit()
    logger.info("whatsapp_dispatch_completed", **counts)
    return {"ok": True, **counts}
