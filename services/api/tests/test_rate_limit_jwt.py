"""Tests for rate limit identity extraction (post-Pass migration).

Verifies that _extract_identity() uses IP-based rate limiting
since KB can no longer locally decode Pass JWT.
"""

from unittest.mock import MagicMock

import pytest


def _make_middleware():
    """Create a RateLimitMiddleware instance for testing."""
    from app.middleware.rate_limit import RateLimitMiddleware

    middleware = RateLimitMiddleware.__new__(RateLimitMiddleware)
    middleware._redis = None
    return middleware


def _make_request(client_ip: str = "127.0.0.1"):
    """Create a mock Starlette Request."""
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = client_ip
    return request


class TestExtractIdentity:
    """_extract_identity() always uses IP since Pass JWT cannot be decoded locally."""

    def test_uses_ip_identity(self):
        middleware = _make_middleware()
        request = _make_request(client_ip="192.168.1.100")

        identity = middleware._extract_identity(request)
        assert identity == "ip:192.168.1.100"

    def test_unknown_client(self):
        middleware = _make_middleware()
        request = MagicMock()
        request.client = None

        identity = middleware._extract_identity(request)
        assert identity == "ip:unknown"
