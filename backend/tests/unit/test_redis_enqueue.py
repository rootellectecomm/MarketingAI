import pytest

from app.core.config import get_settings, redis_enabled
from app.queues.enqueue import enqueue_webhook_job
from app.queues.provider import get_queue_provider, reset_queue_provider_log


@pytest.mark.asyncio
async def test_enqueue_skips_queue_when_no_provider_configured(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
    get_settings.cache_clear()
    reset_queue_provider_log()

    job_id = await enqueue_webhook_job("log-1", {"object": "whatsapp_business_account"}, "whatsapp")

    assert job_id is None
    assert get_queue_provider() == "inline"
    get_settings.cache_clear()
    reset_queue_provider_log()


def test_local_redis_disabled_outside_development(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    get_settings.cache_clear()
    reset_queue_provider_log()

    assert not redis_enabled()
    assert get_queue_provider() == "inline"

    get_settings.cache_clear()
    reset_queue_provider_log()


def test_local_redis_enabled_in_development(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
    get_settings.cache_clear()
    reset_queue_provider_log()

    assert redis_enabled()
    assert get_queue_provider() == "local_redis"

    get_settings.cache_clear()
    reset_queue_provider_log()


def test_upstash_selected_when_configured(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://example.upstash.io")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "token")
    get_settings.cache_clear()
    reset_queue_provider_log()

    assert get_queue_provider() == "upstash"

    get_settings.cache_clear()
    reset_queue_provider_log()
