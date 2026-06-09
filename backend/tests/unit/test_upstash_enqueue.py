import json
import pytest

from app.core.config import get_settings, upstash_enabled
from app.queues.upstash import clear_upstash_client_cache, enqueue_upstash_webhook_job


@pytest.mark.asyncio
async def test_upstash_enqueue_uses_rest_client(monkeypatch):
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://example.upstash.io")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "token")
    get_settings.cache_clear()
    clear_upstash_client_cache()

    pushed: list[str] = []

    class FakeRedis:
        def rpush(self, key, value):
            pushed.append(value)
            return 1

    monkeypatch.setattr("app.queues.upstash.get_upstash_client", lambda: FakeRedis())

    job_id = await enqueue_upstash_webhook_job("log-1", {"object": "whatsapp_business_account"}, "whatsapp")

    assert job_id is not None
    assert len(pushed) == 1
    payload = json.loads(pushed[0])
    assert payload["log_id"] == "log-1"
    assert payload["channel"] == "whatsapp"
    assert payload["job_id"] == job_id

    get_settings.cache_clear()
    clear_upstash_client_cache()


def test_upstash_enabled_requires_url_and_token(monkeypatch):
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
    get_settings.cache_clear()

    assert not upstash_enabled()

    get_settings.cache_clear()
