"""Tests for project CRUD endpoints."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/v1/projects",
        json={"name": "My Project", "industry_hint": "fintech"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["name"] == "My Project"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/v1/projects",
        json={"name": "P1"},
        headers=auth_headers,
    )
    await client.post(
        "/v1/projects",
        json={"name": "P2"},
        headers=auth_headers,
    )
    resp = await client.get("/v1/projects", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) >= 2
    assert body["meta"]["total"] >= 2


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/v1/projects",
        json={"name": "Get Me"},
        headers=auth_headers,
    )
    project_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/v1/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Get Me"


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/v1/projects/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/v1/projects",
        json={"name": "Old Name"},
        headers=auth_headers,
    )
    project_id = create_resp.json()["data"]["id"]

    resp = await client.patch(
        f"/v1/projects/{project_id}",
        json={"name": "New Name"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/v1/projects",
        json={"name": "Delete Me"},
        headers=auth_headers,
    )
    project_id = create_resp.json()["data"]["id"]

    del_resp = await client.delete(f"/v1/projects/{project_id}", headers=auth_headers)
    assert del_resp.status_code == 200

    get_resp = await client.get(f"/v1/projects/{project_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_no_auth(client: AsyncClient):
    resp = await client.get("/v1/projects")
    assert resp.status_code in (401, 422)
