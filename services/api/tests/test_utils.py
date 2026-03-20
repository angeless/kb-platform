"""Tests for crypto and security utilities."""

import pytest

from app.utils.crypto import (
    _KDF1_PREFIX,
    _derive_key,
    decrypt,
    encrypt,
    mask_api_key,
)
from app.utils.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestCrypto:
    def test_encrypt_decrypt_roundtrip(self):
        secret = "test-secret-key-32-chars-long!!!"
        plaintext = "hello world"
        encrypted = encrypt(plaintext, secret)
        decrypted = decrypt(encrypted, secret)
        assert decrypted == plaintext

    def test_encrypt_produces_different_ciphertext(self):
        secret = "test-secret-key-32-chars-long!!!"
        plaintext = "hello world"
        c1 = encrypt(plaintext, secret)
        c2 = encrypt(plaintext, secret)
        assert c1 != c2  # Different nonces

    def test_decrypt_wrong_key_fails(self):
        secret1 = "key-one-32-chars-long-here!!!!!!"
        secret2 = "key-two-32-chars-long-here!!!!!!"
        encrypted = encrypt("secret data", secret1)
        with pytest.raises(Exception):
            decrypt(encrypted, secret2)

    def test_new_format_has_kdf1_prefix(self):
        """New encrypt output must start with b'KDF1' prefix."""
        secret = "test-secret-key-32-chars-long!!!"
        encrypted = encrypt("test data", secret)
        assert encrypted[:4] == _KDF1_PREFIX

    def test_decrypt_legacy_format(self):
        """Old-format data (no KDF1 prefix) must still be decryptable."""
        import os
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        secret = "test-secret-key-32-chars-long!!!"
        plaintext = "legacy secret"
        # Manually create old-format encrypted data
        key = _derive_key(secret)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        legacy_data = nonce + ciphertext  # No KDF1 prefix

        # New decrypt() should handle it
        assert decrypt(legacy_data, secret) == plaintext

    def test_decrypt_wrong_key_new_format(self):
        """Wrong key should fail for new PBKDF2 format."""
        encrypted = encrypt("secret data", "correct-key-long-enough-32chars!")
        with pytest.raises(Exception):
            decrypt(encrypted, "wrong-key-also-long-enough-32ch!")

    def test_mask_api_key_default(self):
        assert mask_api_key("sk-abc123xyz789") == "***********z789"

    def test_mask_api_key_short(self):
        assert mask_api_key("abc") == "***"

    def test_mask_api_key_custom_visible(self):
        assert mask_api_key("sk-abc123xyz789", visible=6) == "*********xyz789"


class TestSecurity:
    def test_hash_and_verify_password(self):
        password = "my-secure-password"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_verify_wrong_password(self):
        hashed = hash_password("correct-password")
        assert not verify_password("wrong-password", hashed)

    def test_jwt_create_and_decode(self):
        secret = "jwt-test-secret"
        data = {"sub": "user-123", "role": "admin"}
        token = create_access_token(data, secret)
        decoded = decode_access_token(token, secret)
        assert decoded["sub"] == "user-123"
        assert decoded["role"] == "admin"
        assert "exp" in decoded
        assert "iat" in decoded

    def test_jwt_expired_token(self):
        import jwt as pyjwt

        secret = "jwt-test-secret"
        token = create_access_token({"sub": "user"}, secret, expires_minutes=-1)
        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_access_token(token, secret)

    def test_jwt_invalid_token(self):
        import jwt as pyjwt

        with pytest.raises(pyjwt.DecodeError):
            decode_access_token("invalid.token.here", "secret")
