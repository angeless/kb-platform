"""Tests for model provider and route endpoints."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_provider(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/v1/model-providers",
        json={
            "provider_name": "openai",
            "api_key": "sk-test-1234567890abcdef",
            "base_url": "https://api.openai.com",
            "timeout_seconds": 30,
            "max_context": 8192,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["provider_name"] == "openai"
    # Verify key is masked
    assert "****" in data["api_key_masked"]
    assert data["api_key_masked"] != "sk-test-1234567890abcdef"


@pytest.mark.asyncio
async def test_list_providers(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/v1/model-providers",
        json={"provider_name": "anthropic", "api_key": "sk-ant-test-key"},
        headers=auth_headers,
    )
    resp = await client.get("/v1/model-providers", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_create_route(client: AsyncClient, auth_headers: dict):
    # First create a provider
    prov_resp = await client.post(
        "/v1/model-providers",
        json={"provider_name": "route-test-provider", "api_key": "sk-route-test"},
        headers=auth_headers,
    )
    provider_id = prov_resp.json()["data"]["id"]

    resp = await client.post(
        "/v1/model-routes",
        json={
            "task_type": "ingest",
            "provider_id": provider_id,
            "model_name": "gpt-4",
            "priority": 1,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["task_type"] == "ingest"
    assert data["model_name"] == "gpt-4"


@pytest.mark.asyncio
async def test_list_routes(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/v1/model-routes", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


@pytest.mark.asyncio
async def test_update_route(client: AsyncClient, auth_headers: dict):
    # Create provider and route
    prov_resp = await client.post(
        "/v1/model-providers",
        json={"provider_name": "update-route-provider", "api_key": "sk-update-test"},
        headers=auth_headers,
    )
    provider_id = prov_resp.json()["data"]["id"]

    route_resp = await client.post(
        "/v1/model-routes",
        json={
            "task_type": "classify",
            "provider_id": provider_id,
            "model_name": "gpt-3.5",
            "priority": 0,
        },
        headers=auth_headers,
    )
    route_id = route_resp.json()["data"]["id"]

    resp = await client.patch(
        f"/v1/model-routes/{route_id}",
        json={"model_name": "gpt-4", "priority": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["model_name"] == "gpt-4"
    assert resp.json()["data"]["priority"] == 5


@pytest.mark.asyncio
async def test_delete_route(client: AsyncClient, auth_headers: dict):
    # Create provider and route
    prov_resp = await client.post(
        "/v1/model-providers",
        json={"provider_name": "delete-route-provider", "api_key": "sk-delete-test"},
        headers=auth_headers,
    )
    provider_id = prov_resp.json()["data"]["id"]

    route_resp = await client.post(
        "/v1/model-routes",
        json={
            "task_type": "review_publish",
            "provider_id": provider_id,
            "model_name": "claude-3",
            "priority": 0,
        },
        headers=auth_headers,
    )
    route_id = route_resp.json()["data"]["id"]

    resp = await client.delete(f"/v1/model-routes/{route_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["deleted"] is True
