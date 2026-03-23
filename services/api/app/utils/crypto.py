"""AES-256-GCM encryption utilities and API key masking."""

import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# Format prefixes for versioned encryption
_KDF1_PREFIX = b"KDF1"  # PBKDF2 with deterministic salt (legacy v1)
_KDF2_PREFIX = b"KDF2"  # PBKDF2 with random salt (current v2, M-05)
_PBKDF2_ITERATIONS = 100_000


def _derive_key(secret: str) -> bytes:
    """Derive a 32-byte key from a string secret (pad or truncate).

    Legacy method — kept for decrypting old-format data only.
    """
    key = secret.encode("utf-8")
    if len(key) < 32:
        key = key.ljust(32, b"\0")
    return key[:32]


def _derive_key_pbkdf2(secret: str) -> bytes:
    """Derive a 32-byte key using PBKDF2-HMAC-SHA256 with deterministic salt.

    Legacy v1 — kept for decrypting KDF1-format data only.
    """
    salt = hashlib.sha256(secret.encode("utf-8")).digest()[:16]
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return kdf.derive(secret.encode("utf-8"))


def _derive_key_pbkdf2_random(secret: str, salt: bytes) -> bytes:
    """Derive a 32-byte key using PBKDF2-HMAC-SHA256 with caller-provided salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return kdf.derive(secret.encode("utf-8"))


def encrypt(plaintext: str, secret: str) -> bytes:
    """Encrypt plaintext using AES-256-GCM with PBKDF2-derived key and random salt.

    Returns KDF2(4B) + salt(16B) + nonce(12B) + ciphertext.
    """
    salt = os.urandom(16)
    key = _derive_key_pbkdf2_random(secret, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return _KDF2_PREFIX + salt + nonce + ciphertext


def decrypt(data: bytes, secret: str) -> str:
    """Decrypt AES-256-GCM data back to plaintext.

    Supports three formats (newest first):
    - KDF2: random salt — KDF2(4B) + salt(16B) + nonce(12B) + ciphertext
    - KDF1: deterministic salt — KDF1(4B) + nonce(12B) + ciphertext
    - Legacy: padded key — nonce(12B) + ciphertext
    """
    if data[:4] == _KDF2_PREFIX:
        # v2 format: KDF2(4B) + salt(16B) + nonce(12B) + ciphertext
        salt = data[4:20]
        key = _derive_key_pbkdf2_random(secret, salt)
        nonce = data[20:32]
        ciphertext = data[32:]
    elif data[:4] == _KDF1_PREFIX:
        # v1 format: KDF1(4B) + nonce(12B) + ciphertext
        key = _derive_key_pbkdf2(secret)
        nonce = data[4:16]
        ciphertext = data[16:]
    else:
        # Legacy format: nonce(12B) + ciphertext
        key = _derive_key(secret)
        nonce = data[:12]
        ciphertext = data[12:]

    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def mask_api_key(api_key: str, visible: int = 4) -> str:
    """Mask an API key, showing only the last `visible` characters."""
    if len(api_key) <= visible:
        return "*" * len(api_key)
    return "*" * (len(api_key) - visible) + api_key[-visible:]
