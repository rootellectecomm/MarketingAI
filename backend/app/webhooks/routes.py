import json
import os

import structlog
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import get_session
from app.models.entities import WebhookLog
from app.models.enums import EventStatus, ProviderType
from app.queues.enqueue import enqueue_webhook_job
from app.services.event_processor import process_webhook_payload
from app.webhooks.meta import verify_meta_signature, webhook_fingerprint
from app.webhooks.verify import verify_meta_hub_challenge

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/webhooks/meta", tags=["meta webhooks"])


@router.get("/instagram", response_class=PlainTextResponse)
async def verify_instagram(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    return verify_meta_hub_challenge(hub_mode, hub_verify_token, hub_challenge)


@router.get("/whatsapp", response_class=PlainTextResponse)
async def verify_whatsapp(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    return verify_meta_hub_challenge(hub_mode, hub_verify_token, hub_challenge)


@router.post("/instagram")
async def receive_instagram(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await _receive_webhook(request, session, channel="instagram")


@router.post("/whatsapp")
async def receive_whatsapp(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await _receive_webhook(request, session, channel="whatsapp")


def _resolve_webhook_target(channel: str) -> tuple[ProviderType, str]:
    settings = get_settings()
    if channel == "whatsapp":
        return ProviderType.whatsapp_cloud, "whatsapp"
    provider = ProviderType.mock if settings.provider_mode == "mock" else ProviderType(settings.provider_mode)
    return provider, "instagram"


async def _process_webhook_inline(log_id: str, payload: dict, channel: str, *, reason: str) -> None:
    logger.info("processing inline", log_id=log_id, channel=channel, reason=reason)
    try:
        await process_webhook_payload(log_id, payload, channel, inline=True)
    except Exception as exc:
        logger.exception(
            "inline processing failed",
            log_id=log_id,
            channel=channel,
            error=str(exc),
        )


async def _receive_webhook(
    request: Request,
    session: AsyncSession,
    channel: str,
) -> dict:
    settings = get_settings()
    raw_body = await request.body()
    signature = request.headers.get("x-hub-signature-256")
    signature_valid = verify_meta_signature(raw_body, signature, settings.meta_app_secret)
    if not signature_valid:
        logger.warning(
            "meta_webhook_signature_invalid",
            channel=channel,
            path=request.url.path,
            environment=settings.environment,
        )

    payload = json.loads(raw_body.decode() or "{}")
    if channel == "instagram" and payload.get("object") == "whatsapp_business_account":
        channel = "whatsapp"
    provider, channel = _resolve_webhook_target(channel)
    if channel == "whatsapp":
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                for message in (change.get("value") or {}).get("messages", []):
                    logger.info(
                        "whatsapp message received",
                        message_id=message.get("id"),
                        sender=message.get("from"),
                        message_type=message.get("type"),
                    )
    log = WebhookLog(
        provider=provider,
        event_id=webhook_fingerprint(payload),
        signature_valid=signature_valid,
        status=EventStatus.received,
        request_headers=dict(request.headers),
        raw_payload=payload,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)

    job_id = await enqueue_webhook_job(log.id, payload, channel)
    processed_inline = False
    inline_reason = "queue_unavailable"

    if job_id:
        log.status = EventStatus.queued
        await session.commit()
        if os.getenv("VERCEL"):
            inline_reason = "serverless_after_enqueue"
            await _process_webhook_inline(log.id, payload, channel, reason=inline_reason)
            processed_inline = True
    else:
        await _process_webhook_inline(log.id, payload, channel, reason=inline_reason)
        processed_inline = True

    return {
        "ok": True,
        "log_id": log.id,
        "job_id": job_id,
        "processed_inline": processed_inline,
        "signature_valid": signature_valid,
    }
