"""Tests for Prometheus metrics endpoint and middleware."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_format(client: AsyncClient):
    """GET /metrics should return Prometheus text format."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    # Should contain at least the standard Python process metrics
    assert "python_info" in body or "process_" in body or "http_" in body


@pytest.mark.asyncio
async def test_metrics_contain_http_request_counters(client: AsyncClient):
    """After making requests, http_requests_total should appear in /metrics."""
    # Make a request to generate metrics
    await client.get("/healthz")

    resp = await client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    # http_requests_total should be defined
    assert "http_requests_total" in body


@pytest.mark.asyncio
async def test_metrics_contain_duration_histogram(client: AsyncClient):
    """http_request_duration_seconds histogram should appear in /metrics."""
    await client.get("/healthz")

    resp = await client.get("/metrics")
    body = resp.text
    assert "http_request_duration_seconds" in body
