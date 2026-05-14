from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_session
from app.models.entities import Conversation, Message

router = APIRouter(prefix="/conversations", tags=["conversations"], dependencies=[Depends(get_current_user)])


@router.get("")
async def list_conversations(session: AsyncSession = Depends(get_session), limit: int = 50) -> list[dict]:
    result = await session.execute(select(Conversation).order_by(Conversation.updated_at.desc()).limit(min(limit, 200)))
    return [
        {
            "id": item.id,
            "external_user_id": item.external_user_id,
            "username": item.username,
            "channel": item.channel,
            "last_message_at": item.last_message_at,
            "is_open": item.is_open,
        }
        for item in result.scalars().all()
    ]


@router.get("/{conversation_id}/messages")
async def list_messages(conversation_id: str, session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).limit(200)
    )
    return [
        {
            "id": item.id,
            "direction": item.direction,
            "body": item.body,
            "channel": item.channel,
            "created_at": item.created_at,
        }
        for item in result.scalars().all()
    ]

