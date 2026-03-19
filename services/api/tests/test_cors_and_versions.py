"""Tests for CORS configuration and /api/versions endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_versions_returns_active_v1(client: AsyncClient):
    """GET /api/versions should return v1 as active."""
    resp = await client.get("/api/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert "versions" in data
    assert len(data["versions"]) == 1
    v1 = data["versions"][0]
    assert v1["version"] == "v1"
    assert v1["status"] == "active"
    assert v1["deprecation_date"] is None


@pytest.mark.asyncio
async def test_cors_headers_on_valid_origin(client: AsyncClient):
    """Request with allowed Origin should get CORS headers in response."""
    resp = await client.get(
        "/healthz",
        headers={"Origin": "http://localhost:3000"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_cors_preflight_options(client: AsyncClient):
    """OPTIONS preflight request should return CORS allow headers."""
    resp = await client.options(
        "/healthz",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "POST" in resp.headers.get("access-control-allow-methods", "")


@pytest.mark.asyncio
async def test_cors_disallowed_origin(client: AsyncClient):
    """Request with disallowed Origin should NOT get CORS headers."""
    resp = await client.get(
        "/healthz",
        headers={"Origin": "http://evil.example.com"},
    )
    assert resp.status_code == 200
    # Disallowed origin: no access-control-allow-origin header
    assert "access-control-allow-origin" not in resp.headers
