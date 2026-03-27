"""Tests for login lockout mechanism (H-08)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from shared_errors import AppException, ErrorCode

# We test the AuthService lockout methods in isolation using mocked Redis


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.redis_url = "redis://localhost:6379/0"
    settings.jwt_secret = "test-secret"
    settings.jwt_algorithm = "HS256"
    settings.access_token_expire_minutes = 30
    settings.refresh_token_expire_days = 7
    settings.environment = "development"
    return settings


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.ttl = AsyncMock(return_value=-2)  # key not found
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock()
    r.setex = AsyncMock()
    r.delete = AsyncMock()
    return r


@pytest.mark.asyncio
async def test_check_lockout_not_locked(mock_db, mock_settings, mock_redis):
    """No lockout key → login allowed."""
    from app.services.auth_service import AuthService

    svc = AuthService(mock_db, mock_settings)
    svc._redis = mock_redis
    mock_redis.ttl.return_value = -2  # key does not exist

    # Should not raise
    await svc._check_lockout("test@example.com")


@pytest.mark.asyncio
async def test_check_lockout_locked(mock_db, mock_settings, mock_redis):
    """Active lockout key → 423 raised."""
    from app.services.auth_service import AuthService

    svc = AuthService(mock_db, mock_settings)
    svc._redis = mock_redis
    mock_redis.ttl.return_value = 600  # 10 minutes remaining

    with pytest.raises(AppException) as exc_info:
        await svc._check_lockout("locked@example.com")
    assert exc_info.value.status_code == 423
    assert "锁定" in exc_info.value.message


@pytest.mark.asyncio
async def test_record_failed_attempt_increments(mock_db, mock_settings, mock_redis):
    """Failed attempts are counted via Redis INCR."""
    from app.services.auth_service import AuthService

    svc = AuthService(mock_db, mock_settings)
    svc._redis = mock_redis
    mock_redis.incr.return_value = 3  # 3rd attempt

    await svc._record_failed_attempt("test@example.com")

    mock_redis.incr.assert_called_once_with("login:attempts:test@example.com")
    mock_redis.setex.assert_not_called()  # not yet at threshold


@pytest.mark.asyncio
async def test_record_failed_attempt_triggers_lockout(mock_db, mock_settings, mock_redis):
    """5th failed attempt triggers lockout."""
    from app.services.auth_service import AuthService

    svc = AuthService(mock_db, mock_settings)
    svc._redis = mock_redis
    mock_redis.incr.return_value = 5  # 5th attempt = threshold

    await svc._record_failed_attempt("test@example.com")

    mock_redis.setex.assert_called_once_with("login:lockout:test@example.com", 900, "1")
    mock_redis.delete.assert_called_once_with("login:attempts:test@example.com")


@pytest.mark.asyncio
async def test_clear_login_attempts(mock_db, mock_settings, mock_redis):
    """Successful login clears both keys."""
    from app.services.auth_service import AuthService

    svc = AuthService(mock_db, mock_settings)
    svc._redis = mock_redis

    await svc._clear_login_attempts("test@example.com")

    mock_redis.delete.assert_called_once_with(
        "login:attempts:test@example.com",
        "login:lockout:test@example.com",
    )


@pytest.mark.asyncio
async def test_lockout_fail_open_when_redis_unavailable(mock_db, mock_settings):
    """If Redis is unavailable, lockout check passes (fail-open)."""
    from app.services.auth_service import AuthService

    svc = AuthService(mock_db, mock_settings)
    svc._redis = None  # will try to connect

    with patch("app.services.auth_service.aioredis.from_url", side_effect=ConnectionError("refused")):
        # Should not raise — fail-open
        await svc._check_lockout("test@example.com")
