from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.schemas.social import ProviderStatus

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_user)])


@router.get("/providers", response_model=ProviderStatus)
async def provider_status() -> ProviderStatus:
    settings = get_settings()
    return ProviderStatus(
        provider_mode=settings.provider_mode,
        instagram_ready=settings.provider_mode != "mock",
        whatsapp_ready=bool(settings.whatsapp_access_token and settings.whatsapp_phone_number_id),
        openai_ready=bool(settings.openai_api_key),
        chroma_collection=settings.chroma_collection,
    )
