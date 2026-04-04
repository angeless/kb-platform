"""High-risk operation confirmation codes.

Generates and verifies one-time confirmation codes stored in Redis.
Used for dangerous operations like project deletion, architecture publish, doc rollback.
"""

import hmac
import logging
import secrets
import time
import uuid

logger = logging.getLogger(__name__)

CONFIRMATION_TTL = 300  # 5 minutes


def generate_confirmation(action: str, user_id: str) -> dict:
    """Generate a 6-digit confirmation code, stored in Redis.

    Returns {"confirmation_id": str, "code": str, "expires_in": int}.
    Falls back to in-memory dict if Redis unavailable.
    """
    code = f"{secrets.randbelow(1000000):06d}"
    confirmation_id = str(uuid.uuid4())

    try:
        from shared_config.settings import get_redis_client
        r = get_redis_client()
        try:
            key = f"confirm:{confirmation_id}"
            r.setex(key, CONFIRMATION_TTL, f"{code}:{user_id}:{action}")
        finally:
            r.close()
    except Exception as e:
        logger.warning("Redis unavailable for confirmation codes: %s — using memory fallback", e)
        _memory_set(confirmation_id, f"{code}:{user_id}:{action}")

    return {"confirmation_id": confirmation_id, "code": code, "expires_in": CONFIRMATION_TTL}


def verify_confirmation(confirmation_id: str, code: str, user_id: str) -> bool:
    """Verify a confirmation code. One-time use — deleted after verification.

    Returns True if valid, False otherwise.
    """
    try:
        from shared_config.settings import get_redis_client
        r = get_redis_client()
        try:
            key = f"confirm:{confirmation_id}"
            stored = r.get(key)
            if stored:
                stored_str = stored.decode() if isinstance(stored, bytes) else stored
                stored_code, stored_user, _action = stored_str.split(":", 2)
                if hmac.compare_digest(stored_code, code) and hmac.compare_digest(stored_user, user_id):
                    r.delete(key)
                    return True
        finally:
            r.close()
    except Exception as e:
        logger.warning("Redis verification failed: %s — trying memory fallback", e)
        stored = _memory_store.pop(confirmation_id, None)
        if stored:
            stored_code, stored_user, _action = stored.split(":", 2)
            return hmac.compare_digest(stored_code, code) and hmac.compare_digest(stored_user, user_id)

    return False


# In-memory fallback with TTL eviction (I-001 fix)
_memory_store: dict[str, str] = {}
_memory_expiry: dict[str, float] = {}


def _memory_set(key: str, value: str) -> None:
    _memory_store[key] = value
    _memory_expiry[key] = time.time() + CONFIRMATION_TTL
    # Evict expired entries
    now = time.time()
    expired = [k for k, exp in _memory_expiry.items() if exp < now]
    for k in expired:
        _memory_store.pop(k, None)
        _memory_expiry.pop(k, None)
