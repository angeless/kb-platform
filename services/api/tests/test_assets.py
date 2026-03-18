"""Tests for asset endpoints."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_asset(client: AsyncClient, auth_headers: dict):
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Asset Upload Project"},
        headers=auth_headers,
    )
    project_id = proj_resp.json()["data"]["id"]

    resp = await client.post(
        "/v1/assets/upload",
        data={"project_id": project_id, "asset_type": "document"},
        files={"file": ("test.txt", b"hello world content", "text/plain")},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["filename"] == "test.txt"
    assert data["parse_status"] == "pending"
    assert data["file_hash"] is not None


@pytest.mark.asyncio
async def test_list_assets(client: AsyncClient, auth_headers: dict):
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Asset List Project"},
        headers=auth_headers,
    )
    project_id = proj_resp.json()["data"]["id"]

    await client.post(
        "/v1/assets/upload",
        data={"project_id": project_id, "asset_type": "document"},
        files={"file": ("file1.txt", b"content one", "text/plain")},
        headers=auth_headers,
    )
    await client.post(
        "/v1/assets/upload",
        data={"project_id": project_id, "asset_type": "document"},
        files={"file": ("file2.txt", b"content two", "text/plain")},
        headers=auth_headers,
    )

    resp = await client.get(
        f"/v1/assets?project_id={project_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) >= 2
    assert body["meta"]["total"] >= 2


@pytest.mark.asyncio
async def test_get_asset(client: AsyncClient, auth_headers: dict):
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Asset Get Project"},
        headers=auth_headers,
    )
    project_id = proj_resp.json()["data"]["id"]

    create_resp = await client.post(
        "/v1/assets/upload",
        data={"project_id": project_id, "asset_type": "document"},
        files={"file": ("get_me.txt", b"get this content", "text/plain")},
        headers=auth_headers,
    )
    asset_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/v1/assets/{asset_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["filename"] == "get_me.txt"


@pytest.mark.asyncio
async def test_duplicate_hash_rejection(client: AsyncClient, auth_headers: dict):
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Asset Dup Project"},
        headers=auth_headers,
    )
    project_id = proj_resp.json()["data"]["id"]

    file_content = b"duplicate content bytes"
    await client.post(
        "/v1/assets/upload",
        data={"project_id": project_id, "asset_type": "document"},
        files={"file": ("dup1.txt", file_content, "text/plain")},
        headers=auth_headers,
    )

    resp = await client.post(
        "/v1/assets/upload",
        data={"project_id": project_id, "asset_type": "document"},
        files={"file": ("dup2.txt", file_content, "text/plain")},
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_asset_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/v1/assets/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404
