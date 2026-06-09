import pytest

from app.core.config import get_settings
from app.services.providers.meta import WhatsAppCloudProvider


@pytest.mark.asyncio
async def test_whatsapp_send_dm_delegates_to_cloud_api(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "12345")
    get_settings.cache_clear()

    provider = WhatsAppCloudProvider()
    called: dict[str, str] = {}

    async def fake_send_whatsapp_text(phone: str, message: str):
        called["phone"] = phone
        called["message"] = message
        from app.services.providers.base import ProviderActionResult

        return ProviderActionResult(ok=True, provider_action_id="wa-1")

    provider.send_whatsapp_text = fake_send_whatsapp_text  # type: ignore[method-assign]
    result = await provider.send_dm("15551234567", "Hello there")

    assert result.ok
    assert called == {"phone": "15551234567", "message": "Hello there"}
    get_settings.cache_clear()
