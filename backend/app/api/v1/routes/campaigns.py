import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.product_knowledge import ROOTELLECT_PRODUCT_CATALOG
from app.api.dependencies import get_current_user
from app.database.init_db import ensure_schema
from app.database.migrations import run_pending_migrations
from app.database.session import get_session
from app.models.entities import Campaign, CampaignEvent
from app.schemas.crm import (
    CampaignCreate,
    CampaignEventRead,
    CampaignRead,
    CampaignTestRequest,
    CampaignTestResult,
    CampaignUpdate,
)
from app.services.campaign_conversion import ROOTELLECT_WHATSAPP_LINK, CampaignConversionService
from app.services.campaign_matcher import instagram_shortcode

router = APIRouter(prefix="/campaigns", tags=["campaigns"], dependencies=[Depends(get_current_user)])


async def _prepare_campaign_storage() -> None:
    await ensure_schema()
    await asyncio.to_thread(run_pending_migrations)


async def _ensure_default_campaign(session: AsyncSession) -> None:
    existing = await session.scalar(select(Campaign.id).limit(1))
    if existing:
        return
    session.add(
        Campaign(
            name="Mind Calm Stress Campaign",
            status="active",
            platform="both",
            product_key="mind_calm",
            product_name="Mind Calm",
            product_link="https://www.rootellect.com/products/mind-calm",
            followup_link="https://www.rootellect.com/products/mind-calm",
            whatsapp_link=(
                "https://wa.me/918679508311?text=Hi%20Rootellect%2C%20I%20want%20to%20know%20about%20Mind%20Calm"
            ),
            product_focus=["Mind Calm"],
            keyword_triggers=["stress", "sleep", "overthinking", "mind calm", "link", "price", "tired", "brain fog"],
            public_reply_template="Sent you the details in DM.",
            dm_template=(
                "Got it. Mind Calm is the closest fit if your concern is stress, overthinking or sleep quality. "
                "It's non-melatonin and supports calmness + better sleep quality. {{product_link}}"
            ),
            public_reply_enabled=True,
            dm_enabled=True,
            whatsapp_followup_enabled=True,
            ai_followup_enabled=True,
        )
    )
    await session.commit()


def _normalize_campaign_metadata(metadata: dict | None) -> dict:
    metadata = dict(metadata or {})
    urls = [str(item).strip() for item in metadata.get("target_media_urls", []) if str(item).strip()]
    shortcodes = [instagram_shortcode(url) for url in urls]
    metadata["target_media_urls"] = urls
    metadata["target_media_shortcodes"] = sorted({item for item in shortcodes if item})
    metadata.setdefault("target_media_ids", [])
    return metadata


def _product_defaults(product_name: str | None) -> dict:
    if not product_name or product_name not in ROOTELLECT_PRODUCT_CATALOG:
        return {}
    product = ROOTELLECT_PRODUCT_CATALOG[product_name]
    return {
        "product_key": product.name.lower().replace(" ", "_"),
        "product_name": product.name,
        "product_link": product.url,
        "followup_link": product.url,
        "product_focus": [product.name],
    }


def _campaign_data(payload: CampaignCreate | CampaignUpdate, *, exclude_unset: bool = False) -> dict:
    data = payload.model_dump(exclude_unset=exclude_unset)
    if "metadata_json" in data or not exclude_unset:
        data["metadata_json"] = _normalize_campaign_metadata(data.get("metadata_json"))
    product_name = data.get("product_name") or (data.get("product_focus") or [None])[0]
    defaults = _product_defaults(product_name)
    for key, value in defaults.items():
        if not data.get(key):
            data[key] = value
    if (not exclude_unset and not data.get("whatsapp_link")) or ("whatsapp_link" in data and not data.get("whatsapp_link")):
        data["whatsapp_link"] = ROOTELLECT_WHATSAPP_LINK
    return data


def _handle_campaign_db_error(exc: Exception) -> HTTPException:
    message = str(exc)
    if "does not exist" in message or "UndefinedColumn" in message:
        return HTTPException(
            status_code=503,
            detail="Campaign database schema is out of date. Redeploy the backend or run alembic upgrade head.",
        )
    return HTTPException(status_code=500, detail=f"Campaign request failed: {message}")


@router.get("", response_model=list[CampaignRead])
async def list_campaigns(session: AsyncSession = Depends(get_session)) -> list[CampaignRead]:
    try:
        await _prepare_campaign_storage()
        await _ensure_default_campaign(session)
        result = await session.execute(select(Campaign).order_by(Campaign.created_at.desc()))
        return [CampaignRead.model_validate(item) for item in result.scalars().all()]
    except SQLAlchemyError as exc:
        raise _handle_campaign_db_error(exc) from exc


@router.post("", response_model=CampaignRead)
async def create_campaign(payload: CampaignCreate, session: AsyncSession = Depends(get_session)) -> CampaignRead:
    try:
        await _prepare_campaign_storage()
        campaign = Campaign(**_campaign_data(payload))
        session.add(campaign)
        await session.commit()
        await session.refresh(campaign)
        return CampaignRead.model_validate(campaign)
    except SQLAlchemyError as exc:
        await session.rollback()
        raise _handle_campaign_db_error(exc) from exc


@router.post("/test", response_model=CampaignTestResult)
async def test_campaign(payload: CampaignTestRequest, session: AsyncSession = Depends(get_session)) -> CampaignTestResult:
    await _prepare_campaign_storage()
    service = CampaignConversionService()
    campaigns = await service.matcher.match_active(
        session,
        payload.text,
        media_id=payload.post_id,
        platform=payload.platform,
    )
    if not campaigns:
        return CampaignTestResult()

    campaign = campaigns[0]
    preview = service.preview(campaign, payload.text, platform=payload.platform, post_id=payload.post_id)
    return CampaignTestResult(
        matched_campaign=CampaignRead.model_validate(campaign),
        matched_keyword=preview.matched_keyword,
        public_reply_preview=preview.public_reply,
        dm_preview=preview.dm_reply,
        product_selected=preview.product_selected,
        lead_score=preview.lead_score,
        ai_intent=preview.ai_intent,
    )


@router.patch("/{campaign_id}", response_model=CampaignRead)
async def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    session: AsyncSession = Depends(get_session),
) -> CampaignRead:
    try:
        await _prepare_campaign_storage()
        campaign = await session.get(Campaign, campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        for key, value in _campaign_data(payload, exclude_unset=True).items():
            setattr(campaign, key, value)
        await session.commit()
        await session.refresh(campaign)
        return CampaignRead.model_validate(campaign)
    except SQLAlchemyError as exc:
        await session.rollback()
        raise _handle_campaign_db_error(exc) from exc


@router.get("/{campaign_id}/events", response_model=list[CampaignEventRead])
async def campaign_events(
    campaign_id: str,
    session: AsyncSession = Depends(get_session),
    limit: int = 100,
) -> list[CampaignEventRead]:
    try:
        await _prepare_campaign_storage()
        result = await session.execute(
            select(CampaignEvent)
            .where(CampaignEvent.campaign_id == campaign_id)
            .order_by(CampaignEvent.created_at.desc())
            .limit(limit)
        )
        return [CampaignEventRead.model_validate(item) for item in result.scalars().all()]
    except SQLAlchemyError as exc:
        raise _handle_campaign_db_error(exc) from exc
