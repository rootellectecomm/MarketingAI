from app.core.security import decrypt_secret, encrypt_secret, hash_password, verify_password


def test_password_hash_roundtrip():
    hashed = hash_password("ChangeMe123!")

    assert verify_password("ChangeMe123!", hashed)
    assert not verify_password("wrong", hashed)


def test_secret_encryption_roundtrip():
    encrypted = encrypt_secret("meta-token")

    assert encrypted != "meta-token"
    assert decrypt_secret(encrypted) == "meta-token"

