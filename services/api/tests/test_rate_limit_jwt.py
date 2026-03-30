"""Tests for T-36-07: RateLimit JWT expiry verification.

Verifies that _extract_identity() rejects expired JWTs and falls back
to IP-based rate limiting.
"""

import time
import uuid
from unittest.mock import MagicMock, patch

import jwt
import pytest


_JWT_SECRET = "test-secret-key-for-rate-limit-tests"
_JWT_ALGORITHM = "HS256"


def _make_middleware():
    """Create a RateLimitMiddleware instance for testing."""
    from app.middleware.rate_limit import RateLimitMiddleware

    middleware = RateLimitMiddleware.__new__(RateLimitMiddleware)
    middleware._redis = None
    return middleware


def _make_request(token: str | None = None, client_ip: str = "127.0.0.1"):
    """Create a mock Starlette Request."""
    request = MagicMock()
    headers = MagicMock()
    if token:
        headers.get = lambda key, default="": (
            f"Bearer {token}" if key == "Authorization" else default
        )
    else:
        headers.get = lambda key, default="": default
    request.headers = headers
    request.client = MagicMock()
    request.client.host = client_ip
    return request


def _make_valid_token(kb_id: str, exp_offset: int = 3600) -> str:
    """Create a JWT token with given expiry offset from now."""
    payload = {
        "sub": str(uuid.uuid4()),
        "kb_id": kb_id,
        "exp": int(time.time()) + exp_offset,
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def _make_expired_token(kb_id: str) -> str:
    """Create an expired JWT token."""
    payload = {
        "sub": str(uuid.uuid4()),
        "kb_id": kb_id,
        "exp": int(time.time()) - 100,  # expired 100 seconds ago
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


@pytest.fixture
def _mock_settings():
    """Mock get_settings to return test JWT config."""
    settings = MagicMock()
    settings.jwt_secret = _JWT_SECRET
    settings.jwt_algorithm = _JWT_ALGORITHM
    with patch("app.middleware.rate_limit.get_settings", return_value=settings):
        yield settings


class TestExtractIdentity:
    """_extract_identity() JWT expiry handling."""

    def test_valid_jwt_returns_kb_identity(self, _mock_settings):
        middleware = _make_middleware()
        kb_id = str(uuid.uuid4())
        token = _make_valid_token(kb_id)
        request = _make_request(token=token)

        identity = middleware._extract_identity(request)
        assert identity == f"tenant:{kb_id}"

    def test_expired_jwt_falls_back_to_ip(self, _mock_settings):
        middleware = _make_middleware()
        kb_id = str(uuid.uuid4())
        token = _make_expired_token(kb_id)
        request = _make_request(token=token, client_ip="192.168.1.100")

        identity = middleware._extract_identity(request)
        assert identity == "ip:192.168.1.100"

    def test_no_jwt_uses_ip(self, _mock_settings):
        middleware = _make_middleware()
        request = _make_request(token=None, client_ip="10.0.0.1")

        identity = middleware._extract_identity(request)
        assert identity == "ip:10.0.0.1"

    def test_invalid_jwt_signature_falls_back_to_ip(self, _mock_settings):
        middleware = _make_middleware()
        # Create token with wrong secret
        payload = {
            "sub": str(uuid.uuid4()),
            "kb_id": str(uuid.uuid4()),
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, "wrong-secret", algorithm=_JWT_ALGORITHM)
        request = _make_request(token=token, client_ip="172.16.0.1")

        identity = middleware._extract_identity(request)
        assert identity == "ip:172.16.0.1"

    def test_valid_jwt_without_kb_id_falls_back_to_ip(self, _mock_settings):
        """JWT is valid but has no kb_id claim."""
        middleware = _make_middleware()
        payload = {
            "sub": str(uuid.uuid4()),
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)
        request = _make_request(token=token, client_ip="10.0.0.2")

        identity = middleware._extract_identity(request)
        assert identity == "ip:10.0.0.2"
