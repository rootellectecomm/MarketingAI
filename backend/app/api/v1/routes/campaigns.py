from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_session
from app.models.entities import Campaign
from app.schemas.crm import CampaignCreate, CampaignRead

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


@router.get("", response_model=list[CampaignRead])
async def list_campaigns(session: AsyncSession = Depends(get_session)) -> list[CampaignRead]:
    await _ensure_default_campaign(session)
    result = await session.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    return [CampaignRead.model_validate(item) for item in result.scalars().all()]


@router.post("", response_model=CampaignRead)
async def create_campaign(payload: CampaignCreate, session: AsyncSession = Depends(get_session)) -> CampaignRead:
    campaign = Campaign(**payload.model_dump())
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    return CampaignRead.model_validate(campaign)

