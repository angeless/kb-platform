"""AES-256-GCM encryption utilities and API key masking."""

import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# New-format prefix: identifies data encrypted with PBKDF2-derived key
_KDF1_PREFIX = b"KDF1"
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
    """Derive a 32-byte key using PBKDF2-HMAC-SHA256.

    Uses a fixed salt derived from the secret's SHA-256 hash (first 16 bytes).
    """
    salt = hashlib.sha256(secret.encode("utf-8")).digest()[:16]
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return kdf.derive(secret.encode("utf-8"))


def encrypt(plaintext: str, secret: str) -> bytes:
    """Encrypt plaintext using AES-256-GCM with PBKDF2-derived key.

    Returns KDF1(4B) + nonce(12B) + ciphertext.
    """
    key = _derive_key_pbkdf2(secret)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return _KDF1_PREFIX + nonce + ciphertext


def decrypt(data: bytes, secret: str) -> str:
    """Decrypt AES-256-GCM data back to plaintext.

    Supports both new format (KDF1 prefix + PBKDF2 key) and
    legacy format (direct nonce + ciphertext with padded key).
    """
    if data[:4] == _KDF1_PREFIX:
        # New format: KDF1(4B) + nonce(12B) + ciphertext
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
