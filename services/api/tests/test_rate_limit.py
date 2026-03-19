"""Tests for rate limiting middleware."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rate_limit_does_not_block_without_redis(client: AsyncClient, auth_headers: dict):
    """Without Redis, rate limiter should fail open and not block requests."""
    resp = await client.get("/v1/projects", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_exempt_from_rate_limit(client: AsyncClient):
    """Health check endpoints should not be rate limited."""
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert "X-RateLimit-Limit" not in resp.headers
