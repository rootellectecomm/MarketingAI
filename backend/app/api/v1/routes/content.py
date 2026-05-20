from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_user
from app.services.content_generator import ContentGenerator

router = APIRouter(prefix="/content", tags=["content"], dependencies=[Depends(get_current_user)])


class ContentGenerateRequest(BaseModel):
    content_type: str = Field(description="reel_hook | story_idea | carousel | comment_cta | founder_script | ugc_prompt")
    topic: str
    product_focus: list[str] = Field(default_factory=list)
    tone: str = "premium_calm"


@router.post("/generate")
async def generate_content(payload: ContentGenerateRequest) -> dict:
    generator = ContentGenerator()
    return await generator.generate(
        content_type=payload.content_type,
        topic=payload.topic,
        product_focus=payload.product_focus,
        tone=payload.tone,
    )
