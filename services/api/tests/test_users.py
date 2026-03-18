"""Tests for user management endpoints."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/v1/users", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    # At least the test user should exist
    assert len(body["data"]) >= 1
    assert body["meta"]["total"] >= 1


@pytest.mark.asyncio
async def test_invite_user(client: AsyncClient, auth_headers: dict):
    email = f"invite-{uuid.uuid4().hex[:8]}@example.com"
    resp = await client.post(
        "/v1/users/invite",
        json={"email": email, "role": "editor"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["email"] == email
    assert data["role"] == "editor"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_update_user_role(client: AsyncClient, auth_headers: dict):
    email = f"update-{uuid.uuid4().hex[:8]}@example.com"
    invite_resp = await client.post(
        "/v1/users/invite",
        json={"email": email, "role": "viewer"},
        headers=auth_headers,
    )
    user_id = invite_resp.json()["data"]["id"]

    resp = await client.patch(
        f"/v1/users/{user_id}",
        json={"role": "editor"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "editor"


@pytest.mark.asyncio
async def test_disable_user(client: AsyncClient, auth_headers: dict):
    email = f"disable-{uuid.uuid4().hex[:8]}@example.com"
    invite_resp = await client.post(
        "/v1/users/invite",
        json={"email": email, "role": "viewer"},
        headers=auth_headers,
    )
    user_id = invite_resp.json()["data"]["id"]

    resp = await client.delete(f"/v1/users/{user_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "disabled"


@pytest.mark.asyncio
async def test_invite_duplicate_email(client: AsyncClient, auth_headers: dict):
    email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/v1/users/invite",
        json={"email": email, "role": "viewer"},
        headers=auth_headers,
    )
    resp = await client.post(
        "/v1/users/invite",
        json={"email": email, "role": "editor"},
        headers=auth_headers,
    )
    assert resp.status_code == 409
