import hashlib
import hmac

from app.webhooks.meta import verify_meta_signature, webhook_fingerprint


def test_verify_meta_signature_accepts_valid_signature():
    body = b'{"hello":"world"}'
    secret = "secret"
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert verify_meta_signature(body, f"sha256={digest}", secret)


def test_verify_meta_signature_rejects_invalid_signature():
    assert not verify_meta_signature(b"{}", "sha256=bad", "secret")


def test_webhook_fingerprint_is_stable_for_key_order():
    left = {"entry": [{"a": 1, "b": 2}]}
    right = {"entry": [{"b": 2, "a": 1}]}

    assert webhook_fingerprint(left) == webhook_fingerprint(right)

