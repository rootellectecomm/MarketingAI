from app.core.config import get_settings
from app.core.security import decrypt_secret
from app.models.entities import ProviderCredential, WhatsAppAccount
from app.models.enums import ProviderType
from app.services.providers.meta import FacebookPageBackedProvider, InstagramProfessionalProvider, WhatsAppCloudProvider
from app.services.providers.mock import MockMetaProvider
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def get_instagram_provider(access_token: str | None = None):
    settings = get_settings()
    if settings.provider_mode == "instagram_professional":
        return InstagramProfessionalProvider(access_token=access_token)
    if settings.provider_mode == "facebook_page_backed":
        return FacebookPageBackedProvider(access_token=access_token)
    return MockMetaProvider()


async def get_whatsapp_provider(session: AsyncSession | None = None):
    settings = get_settings()
    if session is not None:
        credential = await session.scalar(
            select(ProviderCredential)
            .where(
                ProviderCredential.provider_type == ProviderType.whatsapp_cloud,
                ProviderCredential.is_active.is_(True),
                ProviderCredential.encrypted_access_token.is_not(None),
            )
            .order_by(ProviderCredential.updated_at.desc())
            .limit(1)
        )
        if credential and credential.encrypted_access_token:
            account = await session.scalar(
                select(WhatsAppAccount)
                .where(
                    WhatsAppAccount.provider_credential_id == credential.id,
                    WhatsAppAccount.is_active.is_(True),
                )
                .order_by(WhatsAppAccount.updated_at.desc())
                .limit(1)
            )
            if account:
                return WhatsAppCloudProvider(
                    access_token=decrypt_secret(credential.encrypted_access_token),
                    phone_number_id=account.phone_number_id,
                )

    if settings.whatsapp_access_token and settings.whatsapp_phone_number_id:
        return WhatsAppCloudProvider(access_token=settings.whatsapp_access_token, phone_number_id=settings.whatsapp_phone_number_id)
    return MockMetaProvider()
