"""Unit tests for confirmation.py — typed-phrase confirmation for high-risk ops."""

from unittest.mock import patch

from app.utils.confirmation import generate_confirmation, verify_confirmation, _memory_store, _memory_expiry


def _force_memory_fallback():
    """Patch Redis to be unavailable, forcing in-memory fallback."""
    return patch("shared_config.settings.get_redis_client", side_effect=Exception("no redis"))


class TestGenerateConfirmation:
    def test_returns_confirmation_id_and_ttl(self):
        _memory_store.clear()
        _memory_expiry.clear()
        with _force_memory_fallback():
            result = generate_confirmation("delete_project", "user123", "My Project")
        assert "confirmation_id" in result
        assert result["expires_in"] == 300
        # Should NOT contain the phrase in the response
        assert "phrase" not in result
        assert "My Project" not in str(result)

    def test_stores_in_memory_on_redis_failure(self):
        _memory_store.clear()
        _memory_expiry.clear()
        with _force_memory_fallback():
            result = generate_confirmation("delete", "user1", "CONFIRM")
        assert result["confirmation_id"] in _memory_store


class TestVerifyConfirmation:
    def test_valid_phrase_returns_true(self):
        _memory_store.clear()
        _memory_expiry.clear()
        with _force_memory_fallback():
            result = generate_confirmation("delete", "user1", "CONFIRM")
        with _force_memory_fallback():
            assert verify_confirmation(result["confirmation_id"], "CONFIRM", "user1") is True

    def test_wrong_phrase_returns_false_but_token_survives(self):
        _memory_store.clear()
        _memory_expiry.clear()
        with _force_memory_fallback():
            result = generate_confirmation("delete", "user1", "CONFIRM")
        with _force_memory_fallback():
            assert verify_confirmation(result["confirmation_id"], "WRONG", "user1") is False
        # Token should survive — correct retry must still work
        with _force_memory_fallback():
            assert verify_confirmation(result["confirmation_id"], "CONFIRM", "user1") is True

    def test_wrong_user_returns_false(self):
        _memory_store.clear()
        _memory_expiry.clear()
        with _force_memory_fallback():
            result = generate_confirmation("delete", "user1", "CONFIRM")
        with _force_memory_fallback():
            assert verify_confirmation(result["confirmation_id"], "CONFIRM", "wrong_user") is False

    def test_one_time_use(self):
        _memory_store.clear()
        _memory_expiry.clear()
        with _force_memory_fallback():
            result = generate_confirmation("delete", "user1", "CONFIRM")
        with _force_memory_fallback():
            verify_confirmation(result["confirmation_id"], "CONFIRM", "user1")
        # Second attempt should fail (consumed)
        with _force_memory_fallback():
            assert verify_confirmation(result["confirmation_id"], "CONFIRM", "user1") is False

    def test_nonexistent_id_returns_false(self):
        with _force_memory_fallback():
            assert verify_confirmation("nonexistent-id", "CONFIRM", "user1") is False

    def test_phrase_with_colons(self):
        """Phrases containing colons (e.g. project names) must not be corrupted."""
        _memory_store.clear()
        _memory_expiry.clear()
        phrase = "Server:Production:v2"
        with _force_memory_fallback():
            result = generate_confirmation("delete_project", "user1", phrase)
        with _force_memory_fallback():
            assert verify_confirmation(result["confirmation_id"], phrase, "user1") is True

    def test_phrase_with_special_chars(self):
        """Phrases with unicode and special characters must work."""
        _memory_store.clear()
        _memory_expiry.clear()
        phrase = "我的项目 (test) #1"
        with _force_memory_fallback():
            result = generate_confirmation("delete", "user1", phrase)
        with _force_memory_fallback():
            assert verify_confirmation(result["confirmation_id"], phrase, "user1") is True
