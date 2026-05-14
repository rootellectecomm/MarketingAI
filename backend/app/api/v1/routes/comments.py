from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_session
from app.models.entities import Comment
from app.schemas.social import CommentRead

router = APIRouter(prefix="/comments", tags=["comments"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[CommentRead])
async def list_comments(session: AsyncSession = Depends(get_session), limit: int = 50) -> list[CommentRead]:
    result = await session.execute(select(Comment).order_by(Comment.created_at.desc()).limit(min(limit, 200)))
    return [CommentRead.model_validate(item) for item in result.scalars().all()]

