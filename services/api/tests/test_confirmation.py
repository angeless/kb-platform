"""Unit tests for confirmation.py — high-risk operation confirmation codes."""

from unittest.mock import MagicMock, patch

from app.utils.confirmation import generate_confirmation, verify_confirmation, _memory_store, _memory_expiry


class TestGenerateConfirmation:
    def test_returns_6_digit_code(self):
        with patch("app.utils.confirmation.redis", create=True):
            with patch("redis.from_url", side_effect=Exception("no redis")):
                result = generate_confirmation("delete_project", "user123")
        assert len(result["code"]) == 6
        assert result["code"].isdigit()
        assert "confirmation_id" in result
        assert result["expires_in"] == 300

    def test_stores_in_memory_on_redis_failure(self):
        _memory_store.clear()
        _memory_expiry.clear()
        with patch("redis.from_url", side_effect=Exception("no redis")):
            result = generate_confirmation("delete", "user1")
        assert result["confirmation_id"] in _memory_store


class TestVerifyConfirmation:
    def test_valid_code_returns_true(self):
        _memory_store.clear()
        _memory_expiry.clear()
        with patch("redis.from_url", side_effect=Exception("no redis")):
            result = generate_confirmation("delete", "user1")
        with patch("redis.from_url", side_effect=Exception("no redis")):
            assert verify_confirmation(result["confirmation_id"], result["code"], "user1") is True

    def test_wrong_code_returns_false(self):
        _memory_store.clear()
        _memory_expiry.clear()
        with patch("redis.from_url", side_effect=Exception("no redis")):
            result = generate_confirmation("delete", "user1")
        with patch("redis.from_url", side_effect=Exception("no redis")):
            assert verify_confirmation(result["confirmation_id"], "000000", "user1") is False

    def test_wrong_user_returns_false(self):
        _memory_store.clear()
        _memory_expiry.clear()
        with patch("redis.from_url", side_effect=Exception("no redis")):
            result = generate_confirmation("delete", "user1")
        with patch("redis.from_url", side_effect=Exception("no redis")):
            assert verify_confirmation(result["confirmation_id"], result["code"], "wrong_user") is False

    def test_one_time_use(self):
        _memory_store.clear()
        _memory_expiry.clear()
        with patch("redis.from_url", side_effect=Exception("no redis")):
            result = generate_confirmation("delete", "user1")
        with patch("redis.from_url", side_effect=Exception("no redis")):
            verify_confirmation(result["confirmation_id"], result["code"], "user1")
        # Second attempt should fail (code consumed)
        with patch("redis.from_url", side_effect=Exception("no redis")):
            assert verify_confirmation(result["confirmation_id"], result["code"], "user1") is False

    def test_nonexistent_id_returns_false(self):
        with patch("redis.from_url", side_effect=Exception("no redis")):
            assert verify_confirmation("nonexistent-id", "123456", "user1") is False
