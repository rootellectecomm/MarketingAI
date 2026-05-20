from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_session
from app.models.entities import KnowledgeDocument
from app.ai.rag import RAGKnowledgeBase
from app.schemas.crm import KnowledgeCreate, KnowledgeRead

router = APIRouter(prefix="/knowledge", tags=["knowledge"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[KnowledgeRead])
async def list_knowledge(session: AsyncSession = Depends(get_session)) -> list[KnowledgeRead]:
    result = await session.execute(select(KnowledgeDocument).order_by(KnowledgeDocument.updated_at.desc()))
    return [KnowledgeRead.model_validate(item) for item in result.scalars().all()]


@router.post("", response_model=KnowledgeRead)
async def create_knowledge(payload: KnowledgeCreate, session: AsyncSession = Depends(get_session)) -> KnowledgeRead:
    document = KnowledgeDocument(**payload.model_dump())
    session.add(document)
    await session.commit()
    await session.refresh(document)
    rag = RAGKnowledgeBase()
    await rag.index_document(document.title, document.category, document.content, doc_id=document.id)
    return KnowledgeRead.model_validate(document)

