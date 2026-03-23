"""Tests for crypto.py random salt (M-05) and backward compatibility."""

import pytest

from app.utils.crypto import encrypt, decrypt, _KDF1_PREFIX, _KDF2_PREFIX


def test_encrypt_produces_kdf2_format():
    """New encrypt() produces KDF2-prefixed data."""
    data = encrypt("hello world", "my-secret")
    assert data[:4] == _KDF2_PREFIX
    # KDF2(4B) + salt(16B) + nonce(12B) + ciphertext
    assert len(data) > 4 + 16 + 12


def test_encrypt_decrypt_roundtrip():
    """encrypt → decrypt roundtrip works."""
    secret = "test-encryption-key-123"
    plaintext = "sensitive data 敏感数据"
    encrypted = encrypt(plaintext, secret)
    decrypted = decrypt(encrypted, secret)
    assert decrypted == plaintext


def test_encrypt_different_ciphertext_each_time():
    """Same plaintext + secret produces different ciphertext (random salt + nonce)."""
    secret = "same-secret"
    plaintext = "same text"
    enc1 = encrypt(plaintext, secret)
    enc2 = encrypt(plaintext, secret)
    assert enc1 != enc2  # different due to random salt and nonce


def test_decrypt_kdf1_backward_compatible():
    """KDF1-format data (deterministic salt) can still be decrypted."""
    # Encrypt using the old KDF1 method manually
    import hashlib
    import os
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

    secret = "old-secret"
    plaintext = "legacy data"

    # Old KDF1 encrypt
    salt = hashlib.sha256(secret.encode()).digest()[:16]
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000)
    key = kdf.derive(secret.encode())
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    kdf1_data = _KDF1_PREFIX + nonce + ct

    # New decrypt should handle it
    result = decrypt(kdf1_data, secret)
    assert result == plaintext


def test_decrypt_legacy_backward_compatible():
    """Legacy format (no prefix, padded key) can still be decrypted."""
    import os
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    secret = "legacy"
    plaintext = "very old data"

    # Legacy encrypt
    raw_key = secret.encode().ljust(32, b"\0")[:32]
    aesgcm = AESGCM(raw_key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    legacy_data = nonce + ct

    # New decrypt should handle it
    result = decrypt(legacy_data, secret)
    assert result == plaintext


def test_decrypt_wrong_secret_raises():
    """Wrong secret raises an error."""
    encrypted = encrypt("data", "correct-secret")
    with pytest.raises(Exception):
        decrypt(encrypted, "wrong-secret")
