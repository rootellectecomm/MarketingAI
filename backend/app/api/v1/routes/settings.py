from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.database.session import get_session
from app.models.entities import InstagramAccount, ProviderCredential
from app.models.enums import ProviderType
from app.schemas.social import ProviderStatus

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_user)])


@router.get("/providers", response_model=ProviderStatus)
async def provider_status(session: AsyncSession = Depends(get_session)) -> ProviderStatus:
    settings = get_settings()
    facebook_credentials = (
        await session.scalar(
            select(func.count())
            .select_from(ProviderCredential)
            .where(
                ProviderCredential.provider_type == ProviderType.facebook_page_backed,
                ProviderCredential.is_active.is_(True),
            )
        )
        or 0
    )
    instagram_accounts = (
        await session.scalar(
            select(func.count()).select_from(InstagramAccount).where(InstagramAccount.is_active.is_(True))
        )
        or 0
    )
    return ProviderStatus(
        provider_mode=settings.provider_mode,
        facebook_ready=facebook_credentials > 0,
        instagram_ready=instagram_accounts > 0,
        whatsapp_ready=bool(settings.whatsapp_access_token and settings.whatsapp_phone_number_id),
        openai_ready=bool(settings.openai_api_key),
        chroma_collection=settings.chroma_collection,
    )
