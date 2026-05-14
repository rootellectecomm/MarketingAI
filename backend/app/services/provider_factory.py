from app.core.config import get_settings
from app.services.providers.meta import FacebookPageBackedProvider, InstagramProfessionalProvider, WhatsAppCloudProvider
from app.services.providers.mock import MockMetaProvider


def get_instagram_provider():
    settings = get_settings()
    if settings.provider_mode == "instagram_professional":
        return InstagramProfessionalProvider()
    if settings.provider_mode == "facebook_page_backed":
        return FacebookPageBackedProvider()
    return MockMetaProvider()


def get_whatsapp_provider():
    settings = get_settings()
    if settings.whatsapp_access_token and settings.whatsapp_phone_number_id:
        return WhatsAppCloudProvider()
    return MockMetaProvider()

