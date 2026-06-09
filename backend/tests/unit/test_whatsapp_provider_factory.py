import pytest

from app.core.config import get_settings
from app.services.provider_factory import get_whatsapp_provider
from app.services.providers.meta import WhatsAppCloudProvider
from app.services.providers.mock import MockMetaProvider


@pytest.mark.asyncio
async def test_whatsapp_provider_uses_mock_only_in_mock_mode(monkeypatch):
    monkeypatch.setenv("PROVIDER_MODE", "mock")
    monkeypatch.delenv("WHATSAPP_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_PHONE_NUMBER_ID", raising=False)
    get_settings.cache_clear()

    provider = await get_whatsapp_provider()

    assert isinstance(provider, MockMetaProvider)
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_whatsapp_provider_live_mode_without_credentials_fails_real_not_mock(monkeypatch):
    monkeypatch.setenv("PROVIDER_MODE", "facebook_page_backed")
    monkeypatch.delenv("WHATSAPP_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_PHONE_NUMBER_ID", raising=False)
    get_settings.cache_clear()

    provider = await get_whatsapp_provider()
    result = await provider.send_whatsapp_text("+15551234567", "Hello")

    assert isinstance(provider, WhatsAppCloudProvider)
    assert not result.ok
    assert result.error == "Missing WhatsApp credentials"
    get_settings.cache_clear()
