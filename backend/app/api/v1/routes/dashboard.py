from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_session
from app.models.entities import ActionAttempt, AiLog, Comment, IntentAnalysis, Lead, ModerationLog
from app.models.enums import ActionStatus, ModerationAction
from app.schemas.dashboard import DashboardMetrics

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)])


@router.get("/metrics", response_model=DashboardMetrics)
async def metrics(session: AsyncSession = Depends(get_session)) -> DashboardMetrics:
    comments = await session.scalar(select(func.count()).select_from(Comment)) or 0
    leads = await session.scalar(select(func.count()).select_from(Lead)) or 0
    actions = (
        await session.scalar(
            select(func.count()).select_from(ActionAttempt).where(ActionAttempt.status == ActionStatus.sent)
        )
        or 0
    )
    escalations = (
        await session.scalar(
            select(func.count()).select_from(ModerationLog).where(ModerationLog.action == ModerationAction.escalate)
        )
        or 0
    )
    avg_confidence = await session.scalar(select(func.avg(AiLog.confidence)).select_from(AiLog)) or 0
    rows = await session.execute(
        select(IntentAnalysis.sentiment, func.count()).group_by(IntentAnalysis.sentiment)
    )
    latest = await session.execute(select(AiLog).order_by(AiLog.created_at.desc()).limit(8))
    return DashboardMetrics(
        comments=int(comments),
        leads=int(leads),
        automated_actions=int(actions),
        escalations=int(escalations),
        avg_ai_confidence=round(float(avg_confidence), 2),
        sentiment={sentiment: int(count) for sentiment, count in rows.all()},
        latest_activity=[
            {"id": item.id, "confidence": item.confidence, "blocked": item.blocked, "created_at": item.created_at.isoformat()}
            for item in latest.scalars().all()
        ],
    )

