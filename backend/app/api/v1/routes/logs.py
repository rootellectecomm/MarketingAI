from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_session
from app.models.entities import AiLog, ModerationLog, WebhookLog
from app.schemas.dashboard import AILogRead, ModerationLogRead
from app.schemas.social import WebhookLogRead

router = APIRouter(tags=["logs"], dependencies=[Depends(get_current_user)])


@router.get("/ai-logs", response_model=list[AILogRead])
async def ai_logs(session: AsyncSession = Depends(get_session), limit: int = 100) -> list[AILogRead]:
    result = await session.execute(select(AiLog).order_by(AiLog.created_at.desc()).limit(min(limit, 200)))
    return [AILogRead.model_validate(item) for item in result.scalars().all()]


@router.get("/moderation", response_model=list[ModerationLogRead])
async def moderation_logs(session: AsyncSession = Depends(get_session), limit: int = 100) -> list[ModerationLogRead]:
    result = await session.execute(select(ModerationLog).order_by(ModerationLog.created_at.desc()).limit(min(limit, 200)))
    return [ModerationLogRead.model_validate(item) for item in result.scalars().all()]


@router.get("/webhooks/logs", response_model=list[WebhookLogRead])
async def webhook_logs(session: AsyncSession = Depends(get_session), limit: int = 100) -> list[WebhookLogRead]:
    result = await session.execute(select(WebhookLog).order_by(WebhookLog.created_at.desc()).limit(min(limit, 200)))
    return [WebhookLogRead.model_validate(item) for item in result.scalars().all()]

