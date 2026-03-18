"""AES-256-GCM encryption utilities and API key masking."""

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _derive_key(secret: str) -> bytes:
    """Derive a 32-byte key from a string secret (pad or truncate)."""
    key = secret.encode("utf-8")
    if len(key) < 32:
        key = key.ljust(32, b"\0")
    return key[:32]


def encrypt(plaintext: str, secret: str) -> bytes:
    """Encrypt plaintext using AES-256-GCM. Returns nonce + ciphertext."""
    key = _derive_key(secret)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce + ciphertext


def decrypt(data: bytes, secret: str) -> str:
    """Decrypt AES-256-GCM data (nonce + ciphertext) back to plaintext."""
    key = _derive_key(secret)
    aesgcm = AESGCM(key)
    nonce = data[:12]
    ciphertext = data[12:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def mask_api_key(api_key: str, visible: int = 4) -> str:
    """Mask an API key, showing only the last `visible` characters."""
    if len(api_key) <= visible:
        return "*" * len(api_key)
    return "*" * (len(api_key) - visible) + api_key[-visible:]
