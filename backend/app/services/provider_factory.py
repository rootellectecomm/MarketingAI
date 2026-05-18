from app.core.config import get_settings
from app.services.providers.meta import FacebookPageBackedProvider, InstagramProfessionalProvider, WhatsAppCloudProvider
from app.services.providers.mock import MockMetaProvider


def get_instagram_provider(access_token: str | None = None):
    settings = get_settings()
    if settings.provider_mode == "instagram_professional":
        return InstagramProfessionalProvider(access_token=access_token)
    if settings.provider_mode == "facebook_page_backed":
        return FacebookPageBackedProvider(access_token=access_token)
    return MockMetaProvider()


def get_whatsapp_provider():
    settings = get_settings()
    if settings.whatsapp_access_token and settings.whatsapp_phone_number_id:
        return WhatsAppCloudProvider()
    return MockMetaProvider()
