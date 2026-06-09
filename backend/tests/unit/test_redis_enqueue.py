import pytest

from app.core.config import get_settings, redis_enabled
from app.queues.enqueue import enqueue_webhook_job


@pytest.mark.asyncio
async def test_enqueue_skips_when_redis_url_missing(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    get_settings.cache_clear()

    job_id = await enqueue_webhook_job("log-1", {"object": "whatsapp_business_account"}, "whatsapp")

    assert job_id is None
    get_settings.cache_clear()


def test_redis_disabled_for_localhost_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    get_settings.cache_clear()

    assert not redis_enabled()

    get_settings.cache_clear()


def test_redis_enabled_when_url_present_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("REDIS_URL", "redis://redis.example.com:6379/0")
    get_settings.cache_clear()

    assert redis_enabled()

    get_settings.cache_clear()
