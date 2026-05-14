from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_session
from app.models.entities import Lead
from app.schemas.crm import LeadRead, LeadUpdate

router = APIRouter(prefix="/leads", tags=["leads"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[LeadRead])
async def list_leads(session: AsyncSession = Depends(get_session), limit: int = 100) -> list[LeadRead]:
    result = await session.execute(select(Lead).order_by(Lead.score.desc(), Lead.updated_at.desc()).limit(min(limit, 200)))
    return [LeadRead.model_validate(item) for item in result.scalars().all()]


@router.patch("/{lead_id}", response_model=LeadRead)
async def update_lead(lead_id: str, payload: LeadUpdate, session: AsyncSession = Depends(get_session)) -> LeadRead:
    lead = await session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    await session.commit()
    await session.refresh(lead)
    return LeadRead.model_validate(lead)

