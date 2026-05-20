from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_session
from app.models.entities import Funnel, FunnelStep, LeadFunnelState
from app.services.funnel_runner import FunnelRunner

router = APIRouter(prefix="/funnels", tags=["funnels"], dependencies=[Depends(get_current_user)])


@router.get("")
async def list_funnels(session: AsyncSession = Depends(get_session)) -> list[dict]:
    await FunnelRunner().ensure_default_funnel(session)
    await session.commit()
    funnels = (await session.execute(select(Funnel).order_by(Funnel.created_at.desc()))).scalars().all()
    output = []
    for funnel in funnels:
        steps = (
            await session.execute(
                select(FunnelStep).where(FunnelStep.funnel_id == funnel.id).order_by(FunnelStep.step_order.asc())
            )
        ).scalars().all()
        enrolled = await session.scalar(
            select(func.count()).select_from(LeadFunnelState).where(LeadFunnelState.funnel_id == funnel.id)
        )
        output.append(
            {
                "id": funnel.id,
                "name": funnel.name,
                "status": funnel.status,
                "description": funnel.description,
                "steps": [
                    {
                        "id": step.id,
                        "step_order": step.step_order,
                        "channel": step.channel,
                        "delay_hours": step.delay_hours,
                        "message_template": step.message_template[:120],
                    }
                    for step in steps
                ],
                "enrolled_leads": enrolled or 0,
            }
        )
    return output
