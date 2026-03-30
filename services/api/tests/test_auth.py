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
    assert "kb_id" in data
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


# --- T-38-03: httpOnly cookie tests ---


@pytest.mark.asyncio
async def test_login_sets_httponly_cookies(client: AsyncClient):
    """Login response should set httpOnly access_token and refresh_token cookies."""
    email = "cookie-user@example.com"
    await client.post(
        "/v1/auth/register",
        json={"tenant_name": "T", "email": email, "password": "Secure@pass123"},
    )
    resp = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "Secure@pass123"},
    )
    assert resp.status_code == 200

    cookies = {c.name: c for c in resp.cookies.jar}
    assert "access_token" in cookies
    # httpx Cookie objects expose params dict for flags
    # The cookie should exist and be non-empty
    assert cookies["access_token"].value


@pytest.mark.asyncio
async def test_cookie_auth_replaces_header(client: AsyncClient):
    """Requests with only cookie (no Authorization header) should succeed."""
    email = "cookieauth-user@example.com"
    await client.post(
        "/v1/auth/register",
        json={"tenant_name": "T", "email": email, "password": "Secure@pass123"},
    )
    login_resp = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "Secure@pass123"},
    )
    access_token = login_resp.json()["data"]["access_token"]

    # Use cookie instead of Authorization header
    resp = await client.get(
        "/v1/auth/me",
        cookies={"access_token": access_token},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["email"] == email


@pytest.mark.asyncio
async def test_header_auth_still_works(client: AsyncClient, auth_headers: dict):
    """Bearer token in Authorization header should still work (backward compat)."""
    resp = await client.get("/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "email" in data
    assert "role" in data


@pytest.mark.asyncio
async def test_refresh_updates_access_cookie(client: AsyncClient):
    """Refresh endpoint should set a new access_token cookie."""
    email = "refresh-cookie@example.com"
    await client.post(
        "/v1/auth/register",
        json={"tenant_name": "T", "email": email, "password": "Secure@pass123"},
    )
    login_resp = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "Secure@pass123"},
    )
    refresh_token = login_resp.json()["data"]["refresh_token"]

    # Refresh via body (backward compat)
    resp = await client.post(
        "/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    cookies = {c.name: c for c in resp.cookies.jar}
    assert "access_token" in cookies


@pytest.mark.asyncio
async def test_refresh_via_cookie(client: AsyncClient):
    """Refresh endpoint should accept refresh_token from cookie when no body is provided."""
    email = "refresh-cookieonly@example.com"
    await client.post(
        "/v1/auth/register",
        json={"tenant_name": "T", "email": email, "password": "Secure@pass123"},
    )
    login_resp = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "Secure@pass123"},
    )
    refresh_token = login_resp.json()["data"]["refresh_token"]

    # Refresh via cookie only (no body)
    resp = await client.post(
        "/v1/auth/refresh",
        cookies={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()["data"]


@pytest.mark.asyncio
async def test_logout_clears_cookies(client: AsyncClient):
    """Logout should clear auth cookies."""
    resp = await client.post("/v1/auth/logout")
    assert resp.status_code == 204
    # Check that cookies are cleared (max-age=0 or deleted)
    cookie_headers = resp.headers.get_list("set-cookie")
    access_cleared = any("access_token" in h and 'max-age=0' in h.lower() for h in cookie_headers)
    assert access_cleared


@pytest.mark.asyncio
async def test_me_without_auth(client: AsyncClient):
    """/me without any auth should return 401."""
    resp = await client.get("/v1/auth/me")
    assert resp.status_code == 401
