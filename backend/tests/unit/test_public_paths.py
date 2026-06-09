from app.core.public_paths import is_public_webhook_path


def test_public_webhook_paths_are_exempt():
    assert is_public_webhook_path("/webhook")
    assert is_public_webhook_path("/webhooks/meta/whatsapp")
    assert is_public_webhook_path("/webhooks/meta/instagram")


def test_api_paths_are_not_public_webhooks():
    assert not is_public_webhook_path("/api/v1/settings/providers")
    assert not is_public_webhook_path("/health")
