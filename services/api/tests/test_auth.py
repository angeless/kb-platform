"""Tests for auth endpoints: register, login, refresh."""

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post(
        "/v1/auth/register",
        json={
            "tenant_name": "Acme Corp",
            "email": "new-user@example.com",
            "password": "Secure@pass123",
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert "tenant_id" in data
    assert "user_id" in data
    assert data["email"] == "new-user@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    email = "dup-user@example.com"
    await client.post(
        "/v1/auth/register",
        json={"tenant_name": "T1", "email": email, "password": "Secure@pass123"},
    )
    resp = await client.post(
        "/v1/auth/register",
        json={"tenant_name": "T2", "email": email, "password": "Secure@pass456"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    email = "login-user@example.com"
    await client.post(
        "/v1/auth/register",
        json={"tenant_name": "T", "email": email, "password": "Secure@pass123"},
    )
    resp = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "Secure@pass123"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    email = "wrongpw-user@example.com"
    await client.post(
        "/v1/auth/register",
        json={"tenant_name": "T", "email": email, "password": "Secure@pass123"},
    )
    resp = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    email = "refresh-user@example.com"
    await client.post(
        "/v1/auth/register",
        json={"tenant_name": "T", "email": email, "password": "Secure@pass123"},
    )
    login_resp = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "Secure@pass123"},
    )
    refresh_token = login_resp.json()["data"]["refresh_token"]

    resp = await client.post(
        "/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "access_token" in data


@pytest.mark.asyncio
async def test_register_weak_password_no_uppercase(client: AsyncClient):
    """Password without uppercase should be rejected."""
    resp = await client.post(
        "/v1/auth/register",
        json={"tenant_name": "T", "email": "weak1@example.com", "password": "secure@pass123"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_weak_password_no_special_char(client: AsyncClient):
    """Password without special character should be rejected."""
    resp = await client.post(
        "/v1/auth/register",
        json={"tenant_name": "T", "email": "weak2@example.com", "password": "SecurePass123"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_weak_password_only_digits(client: AsyncClient):
    """Purely numeric password should be rejected."""
    resp = await client.post(
        "/v1/auth/register",
        json={"tenant_name": "T", "email": "weak3@example.com", "password": "12345678"},
    )
    assert resp.status_code == 422
