"""Tests for deep health check endpoint /api/health/ready."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_ready_all_ok(client: AsyncClient):
    """When all services are up, status should be ok with 200."""
    with patch("app.routers.health._check_redis", new_callable=AsyncMock) as mock_redis, \
         patch("app.routers.health._check_minio", new_callable=AsyncMock) as mock_minio:
        mock_redis.return_value = {"status": "ok", "latency_ms": 2, "message": "PING successful"}
        mock_minio.return_value = {"status": "ok", "latency_ms": 5, "message": "Bucket access OK"}

        resp = await client.get("/api/health/ready")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    from pathlib import Path
    expected_version = Path("VERSION").read_text().strip()
    assert data["version"] == expected_version
    assert "postgres" in data["checks"]
    assert "redis" in data["checks"]
    assert "minio" in data["checks"]


@pytest.mark.asyncio
async def test_health_ready_redis_down_is_degraded(client: AsyncClient):
    """When Redis is down but PG is up, status should be degraded (200)."""
    with patch("app.routers.health._check_redis", new_callable=AsyncMock) as mock_redis, \
         patch("app.routers.health._check_minio", new_callable=AsyncMock) as mock_minio:
        mock_redis.return_value = {"status": "error", "latency_ms": 1000, "message": "Connection refused"}
        mock_minio.return_value = {"status": "ok", "latency_ms": 5, "message": "Bucket access OK"}

        resp = await client.get("/api/health/ready")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_ready_minio_down_is_degraded(client: AsyncClient):
    """When MinIO is down but PG is up, status should be degraded (200)."""
    with patch("app.routers.health._check_redis", new_callable=AsyncMock) as mock_redis, \
         patch("app.routers.health._check_minio", new_callable=AsyncMock) as mock_minio:
        mock_redis.return_value = {"status": "ok", "latency_ms": 2, "message": "PING successful"}
        mock_minio.return_value = {"status": "error", "latency_ms": 1000, "message": "Connection refused"}

        resp = await client.get("/api/health/ready")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_ready_postgres_down_is_unhealthy(client: AsyncClient):
    """When PostgreSQL is down, status should be unhealthy (503)."""
    with patch("app.routers.health._check_postgres", new_callable=AsyncMock) as mock_pg, \
         patch("app.routers.health._check_redis", new_callable=AsyncMock) as mock_redis, \
         patch("app.routers.health._check_minio", new_callable=AsyncMock) as mock_minio:
        mock_pg.return_value = {"status": "error", "latency_ms": 1000, "message": "Connection refused"}
        mock_redis.return_value = {"status": "ok", "latency_ms": 2, "message": "PING successful"}
        mock_minio.return_value = {"status": "ok", "latency_ms": 5, "message": "Bucket access OK"}

        resp = await client.get("/api/health/ready")

    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_health_ready_all_down_is_unhealthy(client: AsyncClient):
    """When all services are down, status should be unhealthy (503)."""
    with patch("app.routers.health._check_postgres", new_callable=AsyncMock) as mock_pg, \
         patch("app.routers.health._check_redis", new_callable=AsyncMock) as mock_redis, \
         patch("app.routers.health._check_minio", new_callable=AsyncMock) as mock_minio:
        mock_pg.return_value = {"status": "error", "latency_ms": 1000, "message": "Timeout"}
        mock_redis.return_value = {"status": "error", "latency_ms": 1000, "message": "Timeout"}
        mock_minio.return_value = {"status": "error", "latency_ms": 1000, "message": "Timeout"}

        resp = await client.get("/api/health/ready")

    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "unhealthy"
