import hashlib
import hmac

from app.webhooks.meta import (
    evaluate_webhook_signature,
    signature_status_to_bool,
    verify_meta_signature,
    webhook_fingerprint,
)


def test_verify_meta_signature_accepts_valid_signature():
    body = b'{"hello":"world"}'
    secret = "secret"
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert verify_meta_signature(body, f"sha256={digest}", secret)


def test_verify_meta_signature_rejects_invalid_signature():
    assert not verify_meta_signature(b"{}", "sha256=bad", "secret")


def test_evaluate_whatsapp_signature_unknown_when_secret_missing():
    body = b'{"object":"whatsapp_business_account"}'

    status = evaluate_webhook_signature(body, "sha256=anything", None, unknown_when_secret_missing=True)

    assert status == "unknown"
    assert signature_status_to_bool(status) is None


def test_evaluate_instagram_signature_invalid_when_secret_missing():
    body = b'{"object":"instagram"}'

    status = evaluate_webhook_signature(body, "sha256=anything", None, unknown_when_secret_missing=False)

    assert status == "invalid"


def test_evaluate_whatsapp_signature_uses_whatsapp_secret_not_meta():
    body = b'{"object":"whatsapp_business_account"}'
    whatsapp_secret = "whatsapp-secret"
    digest = hmac.new(whatsapp_secret.encode(), body, hashlib.sha256).hexdigest()

    status = evaluate_webhook_signature(body, f"sha256={digest}", whatsapp_secret, unknown_when_secret_missing=True)

    assert status == "valid"


def test_webhook_fingerprint_is_stable_for_key_order():
    left = {"entry": [{"a": 1, "b": 2}]}
    right = {"entry": [{"b": 2, "a": 1}]}

    assert webhook_fingerprint(left) == webhook_fingerprint(right)
