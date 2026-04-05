"""High-risk operation confirmation via typed phrase.

Stores a challenge phrase in Redis. The 428 response tells the frontend
what to ask the user (e.g. "type the project name"), but does NOT reveal
the expected answer. The user must type the correct phrase to proceed.

Provides meaningful friction against accidental destructive operations
without requiring out-of-band delivery (email/SMS).
"""

import hmac
import logging
import time
import uuid

logger = logging.getLogger(__name__)

CONFIRMATION_TTL = 300  # 5 minutes


def generate_confirmation(action: str, user_id: str, expected_phrase: str) -> dict:
    """Create a confirmation challenge stored in Redis.

    Args:
        action: The operation name (e.g. "delete_project").
        user_id: The requesting user's ID.
        expected_phrase: The phrase the user must type to confirm.

    Returns:
        {"confirmation_id": str, "expires_in": int}
        NOTE: The expected_phrase is NOT returned — the frontend must prompt
        the user for it independently (e.g. "type the project name").
    """
    confirmation_id = str(uuid.uuid4())
    value = f"{expected_phrase}:{user_id}:{action}"

    try:
        from shared_config.settings import get_redis_client
        r = get_redis_client()
        try:
            key = f"confirm:{confirmation_id}"
            r.setex(key, CONFIRMATION_TTL, value)
        finally:
            r.close()
    except Exception as e:
        logger.warning("Redis unavailable for confirmation: %s — using memory fallback", e)
        _memory_set(confirmation_id, value)

    return {"confirmation_id": confirmation_id, "expires_in": CONFIRMATION_TTL}


def verify_confirmation(confirmation_id: str, phrase: str, user_id: str) -> bool:
    """Verify a typed confirmation phrase. One-time use — deleted after verification.

    Returns True if the phrase matches, False otherwise.
    """
    try:
        from shared_config.settings import get_redis_client
        r = get_redis_client()
        try:
            key = f"confirm:{confirmation_id}"
            stored = r.get(key)
            if stored:
                stored_str = stored.decode() if isinstance(stored, bytes) else stored
                stored_phrase, stored_user, _action = stored_str.split(":", 2)
                if hmac.compare_digest(stored_phrase, phrase) and hmac.compare_digest(stored_user, user_id):
                    r.delete(key)
                    return True
        finally:
            r.close()
    except Exception as e:
        logger.warning("Redis verification failed: %s — trying memory fallback", e)
        stored = _memory_store.pop(confirmation_id, None)
        if stored:
            stored_phrase, stored_user, _action = stored.split(":", 2)
            return hmac.compare_digest(stored_phrase, phrase) and hmac.compare_digest(stored_user, user_id)

    return False


# In-memory fallback with TTL eviction
_memory_store: dict[str, str] = {}
_memory_expiry: dict[str, float] = {}


def _memory_set(key: str, value: str) -> None:
    _memory_store[key] = value
    _memory_expiry[key] = time.time() + CONFIRMATION_TTL
    now = time.time()
    expired = [k for k, exp in _memory_expiry.items() if exp < now]
    for k in expired:
        _memory_store.pop(k, None)
        _memory_expiry.pop(k, None)
