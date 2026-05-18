from fastapi import APIRouter, Depends
from sqlalchemy import select
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
    facebook_credentials = list(
        (
            await session.scalars(
                select(ProviderCredential)
                .where(
                    ProviderCredential.provider_type == ProviderType.facebook_page_backed,
                    ProviderCredential.is_active.is_(True),
                )
                .order_by(ProviderCredential.updated_at.desc())
            )
        ).all()
    )
    instagram_accounts = list(
        (
            await session.scalars(
                select(InstagramAccount).where(InstagramAccount.is_active.is_(True)).order_by(InstagramAccount.updated_at.desc())
            )
        ).all()
    )

    missing_meta_env = [
        key
        for key, value in {
            "META_APP_ID": settings.meta_app_id,
            "META_APP_SECRET": settings.meta_app_secret,
            "META_OAUTH_REDIRECT_URI": settings.meta_oauth_redirect_uri,
            "META_CONNECT_SUCCESS_URL": settings.meta_connect_success_url,
        }.items()
        if not value or str(value).startswith("replace-") or str(value).startswith("change-me")
    ]
    setup_warnings: list[str] = []
    if settings.provider_mode == "mock":
        setup_warnings.append(
            "Backend PROVIDER_MODE is mock. Set PROVIDER_MODE=facebook_page_backed "
            "on the backend Vercel project for real Meta data."
        )
    if missing_meta_env:
        setup_warnings.append(f"Meta OAuth is missing backend env vars: {', '.join(missing_meta_env)}.")
    if not facebook_credentials:
        setup_warnings.append("No Facebook Page token is saved yet. Click Connect Facebook & Instagram after Meta env is set.")
    if facebook_credentials and not instagram_accounts:
        setup_warnings.append("Facebook is connected, but no linked Instagram professional account was returned by Meta.")

    return ProviderStatus(
        provider_mode=settings.provider_mode,
        facebook_ready=len(facebook_credentials) > 0,
        instagram_ready=len(instagram_accounts) > 0,
        whatsapp_ready=bool(settings.whatsapp_access_token and settings.whatsapp_phone_number_id),
        openai_ready=bool(settings.openai_api_key),
        chroma_collection=settings.chroma_collection,
        meta_env_ready=not missing_meta_env,
        missing_meta_env=missing_meta_env,
        setup_warnings=setup_warnings,
        facebook_pages=[
            {
                "id": credential.external_account_id,
                "name": credential.account_name,
                "updated_at": credential.updated_at,
            }
            for credential in facebook_credentials
        ],
        instagram_accounts=[
            {
                "id": account.ig_user_id,
                "username": account.username,
                "auth_path": account.auth_path,
                "updated_at": account.updated_at,
            }
            for account in instagram_accounts
        ],
    )
