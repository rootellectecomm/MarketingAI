from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_session
from app.models.entities import Campaign
from app.schemas.crm import CampaignCreate, CampaignRead, CampaignUpdate
from app.services.campaign_matcher import instagram_shortcode

router = APIRouter(prefix="/campaigns", tags=["campaigns"], dependencies=[Depends(get_current_user)])


async def _ensure_default_campaign(session: AsyncSession) -> None:
    existing = await session.scalar(select(Campaign.id).limit(1))
    if existing:
        return
    session.add(
        Campaign(
            name="Wellness Keyword Automation",
            status="active",
            product_focus=["Mind Calm", "PCOS Support", "Menopause Prime Support"],
            keyword_triggers=["pcos", "stress", "sleep", "hormones", "help", "details", "menopause", "anxiety"],
            public_reply_enabled=True,
            dm_enabled=True,
            whatsapp_followup_enabled=True,
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


@router.get("", response_model=list[CampaignRead])
async def list_campaigns(session: AsyncSession = Depends(get_session)) -> list[CampaignRead]:
    await _ensure_default_campaign(session)
    result = await session.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    return [CampaignRead.model_validate(item) for item in result.scalars().all()]


@router.post("", response_model=CampaignRead)
async def create_campaign(payload: CampaignCreate, session: AsyncSession = Depends(get_session)) -> CampaignRead:
    data = payload.model_dump()
    data["metadata_json"] = _normalize_campaign_metadata(data.get("metadata_json"))
    campaign = Campaign(**data)
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    return CampaignRead.model_validate(campaign)


@router.patch("/{campaign_id}", response_model=CampaignRead)
async def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    session: AsyncSession = Depends(get_session),
) -> CampaignRead:
    campaign = await session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    data = payload.model_dump(exclude_unset=True)
    if "metadata_json" in data:
        data["metadata_json"] = _normalize_campaign_metadata(data["metadata_json"])
    for key, value in data.items():
        setattr(campaign, key, value)
    await session.commit()
    await session.refresh(campaign)
    return CampaignRead.model_validate(campaign)

