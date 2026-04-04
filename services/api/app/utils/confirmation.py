"""High-risk operation confirmation codes.

Generates and verifies one-time confirmation codes stored in Redis.
Used for dangerous operations like project deletion, architecture publish, doc rollback.
"""

import logging
import secrets
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
        import redis
        from shared_config.settings import get_settings
        r = redis.from_url(get_settings().redis_url)
        key = f"confirm:{confirmation_id}"
        r.setex(key, CONFIRMATION_TTL, f"{code}:{user_id}:{action}")
        r.close()
    except Exception as e:
        logger.warning("Redis unavailable for confirmation codes: %s — using memory fallback", e)
        _memory_store[confirmation_id] = f"{code}:{user_id}:{action}"

    return {"confirmation_id": confirmation_id, "code": code, "expires_in": CONFIRMATION_TTL}


def verify_confirmation(confirmation_id: str, code: str, user_id: str) -> bool:
    """Verify a confirmation code. One-time use — deleted after verification.

    Returns True if valid, False otherwise.
    """
    try:
        import redis
        from shared_config.settings import get_settings
        r = redis.from_url(get_settings().redis_url)
        key = f"confirm:{confirmation_id}"
        stored = r.get(key)
        if stored:
            stored_str = stored.decode() if isinstance(stored, bytes) else stored
            stored_code, stored_user, _action = stored_str.split(":", 2)
            if stored_code == code and stored_user == user_id:
                r.delete(key)
                r.close()
                return True
        r.close()
    except Exception as e:
        logger.warning("Redis verification failed: %s — trying memory fallback", e)
        stored = _memory_store.pop(confirmation_id, None)
        if stored:
            stored_code, stored_user, _action = stored.split(":", 2)
            return stored_code == code and stored_user == user_id

    return False


# In-memory fallback (single instance only)
_memory_store: dict[str, str] = {}
