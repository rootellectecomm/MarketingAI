from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.session import get_session
from app.models.entities import WebhookLog
from app.models.enums import EventStatus, ProviderType
from app.services.event_processor import process_webhook_payload
from app.services.provider_factory import get_instagram_provider, get_whatsapp_provider
from app.webhooks.meta import verify_meta_signature, webhook_fingerprint

router = APIRouter(prefix="/webhooks/meta", tags=["meta webhooks"])


@router.get("/instagram")
async def verify_instagram(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> Response:
    challenge = await get_instagram_provider().verify_webhook(hub_mode, hub_verify_token, hub_challenge)
    return Response(content=challenge, media_type="text/plain")


@router.get("/whatsapp")
async def verify_whatsapp(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> Response:
    challenge = await get_whatsapp_provider().verify_webhook(hub_mode, hub_verify_token, hub_challenge)
    return Response(content=challenge, media_type="text/plain")


@router.post("/instagram")
async def receive_instagram(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict:
    settings = get_settings()
    provider = ProviderType.mock if settings.provider_mode == "mock" else ProviderType(settings.provider_mode)
    return await _receive_webhook(request, background_tasks, session, provider, "instagram")


@router.post("/whatsapp")
async def receive_whatsapp(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await _receive_webhook(request, background_tasks, session, ProviderType.whatsapp_cloud, "whatsapp")


async def _receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    provider: ProviderType,
    channel: str,
) -> dict:
    settings = get_settings()
    raw_body = await request.body()
    signature = request.headers.get("x-hub-signature-256")
    signature_valid = verify_meta_signature(raw_body, signature, settings.meta_app_secret)
    if settings.environment == "production" and not signature_valid:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
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
    background_tasks.add_task(process_webhook_payload, log.id, payload, channel)
    return {"ok": True, "log_id": log.id, "signature_valid": signature_valid}
