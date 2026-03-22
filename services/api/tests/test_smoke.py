"""Smoke tests — quick validation that core API endpoints respond correctly.

These tests are designed to run fast (< 30s) and catch fundamental breakages.
Run with: python3 -m pytest services/api/tests/test_smoke.py -v
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Health check endpoint should return 200."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_deep_health_endpoint(client: AsyncClient):
    """Deep health check should return 200 with component statuses."""
    response = await client.get("/health/deep")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_openapi_schema_accessible(client: AsyncClient):
    """OpenAPI schema should be accessible."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "KB Platform API"


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client: AsyncClient):
    """Protected endpoints should reject unauthenticated requests."""
    response = await client.get("/api/v1/projects")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_login_with_invalid_credentials(client: AsyncClient):
    """Login with invalid credentials should return 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cors_headers_present(client: AsyncClient):
    """CORS headers should be present on responses."""
    response = await client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Should not be 405 Method Not Allowed
    assert response.status_code in (200, 204)
