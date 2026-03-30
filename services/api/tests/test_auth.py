"""Tests for auth endpoints: register, login, refresh (via PA Pass)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from shared_errors import ConflictException, ErrorCode, ForbiddenException, UnauthorizedException


# Mock Pass responses
_PASS_REGISTER_RESP = {
    "passId": f"pass:{uuid.uuid4()}",
    "token": "mock-pass-jwt-token-register",
    "expiresAt": "2026-03-29T13:00:00Z",
    "productBinding": {"productId": "mock-product"},
}

_PASS_LOGIN_RESP = {
    "passId": f"pass:{uuid.uuid4()}",
    "token": "mock-pass-jwt-token-login",
    "expiresAt": "2026-03-29T13:00:00Z",
    "productBindings": [],
}

_PASS_REFRESH_RESP = {
    "token": "mock-pass-jwt-token-refreshed",
    "expiresAt": "2026-03-29T14:00:00Z",
}

_PASS_ME_RESP = {
    "passId": _PASS_LOGIN_RESP["passId"],
    "email": "test@example.com",
    "displayName": "Test",
}


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    with patch("app.services.auth_service.PassClient") as MockPassClient:
        mock_pass = AsyncMock()
        mock_pass.register = AsyncMock(return_value=_PASS_REGISTER_RESP)
        MockPassClient.return_value = mock_pass

        resp = await client.post(
            "/v1/auth/register",
            json={"email": "new-user@example.com", "password": "Secure@pass123"},
        )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert "access_token" in data
    assert data["email"] == "new-user@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    with patch("app.services.auth_service.PassClient") as MockPassClient:
        mock_pass = AsyncMock()
        mock_pass.register = AsyncMock(side_effect=ConflictException(
            error_code=ErrorCode.AUTH_EMAIL_ALREADY_EXISTS,
            message="邮箱已注册",
        ))
        MockPassClient.return_value = mock_pass

        resp = await client.post(
            "/v1/auth/register",
            json={"email": "dup@example.com", "password": "Secure@pass123"},
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    with patch("app.services.auth_service.PassClient") as MockPassClient:
        mock_pass = AsyncMock()
        mock_pass.login = AsyncMock(return_value=_PASS_LOGIN_RESP)
        MockPassClient.return_value = mock_pass

        resp = await client.post(
            "/v1/auth/login",
            json={"email": "login@example.com", "password": "Secure@pass123"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    with patch("app.services.auth_service.PassClient") as MockPassClient:
        mock_pass = AsyncMock()
        mock_pass.login = AsyncMock(side_effect=UnauthorizedException(
            error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
            message="邮箱或密码错误",
        ))
        MockPassClient.return_value = mock_pass

        resp = await client.post(
            "/v1/auth/login",
            json={"email": "wrong@example.com", "password": "wrongpassword"},
        )
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_banned_account(client: AsyncClient):
    with patch("app.services.auth_service.PassClient") as MockPassClient:
        mock_pass = AsyncMock()
        mock_pass.login = AsyncMock(side_effect=ForbiddenException(
            error_code=ErrorCode.AUTH_ACCOUNT_BANNED,
            message="账号已被封禁，请联系管理员",
        ))
        MockPassClient.return_value = mock_pass

        resp = await client.post(
            "/v1/auth/login",
            json={"email": "banned@example.com", "password": "Secure@pass123"},
        )
    assert resp.status_code == 403
    assert resp.json()["error_code"] == "AUTH_ACCOUNT_BANNED"
    assert "封禁" in resp.json()["message"]


@pytest.mark.asyncio
async def test_register_weak_password_no_uppercase(client: AsyncClient):
    resp = await client.post(
        "/v1/auth/register",
        json={"email": "weak1@example.com", "password": "secure@pass123"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_weak_password_no_special_char(client: AsyncClient):
    resp = await client.post(
        "/v1/auth/register",
        json={"email": "weak2@example.com", "password": "SecurePass123"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_weak_password_only_digits(client: AsyncClient):
    resp = await client.post(
        "/v1/auth/register",
        json={"email": "weak3@example.com", "password": "12345678"},
    )
    assert resp.status_code == 422


# --- httpOnly cookie tests ---


@pytest.mark.asyncio
async def test_login_sets_httponly_cookie(client: AsyncClient):
    with patch("app.services.auth_service.PassClient") as MockPassClient:
        mock_pass = AsyncMock()
        mock_pass.login = AsyncMock(return_value=_PASS_LOGIN_RESP)
        MockPassClient.return_value = mock_pass

        resp = await client.post(
            "/v1/auth/login",
            json={"email": "cookie-user@example.com", "password": "Secure@pass123"},
        )
    assert resp.status_code == 200
    cookies = {c.name: c for c in resp.cookies.jar}
    assert "access_token" in cookies
    assert cookies["access_token"].value


@pytest.mark.asyncio
async def test_header_auth_still_works(client: AsyncClient, auth_headers: dict):
    """Bearer token in Authorization header should still work."""
    resp = await client.get("/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "email" in data
    assert "role" in data


@pytest.mark.asyncio
async def test_logout_clears_cookies(client: AsyncClient):
    resp = await client.post("/v1/auth/logout")
    assert resp.status_code == 204
    cookie_headers = resp.headers.get_list("set-cookie")
    access_cleared = any("access_token" in h and 'max-age=0' in h.lower() for h in cookie_headers)
    assert access_cleared


@pytest.mark.asyncio
async def test_me_without_auth(client: AsyncClient):
    """/me without any auth should return 401."""
    # Remove dependency override for this test
    from app.deps import get_current_user
    app = client._transport.app  # type: ignore[union-attr]
    original = app.dependency_overrides.pop(get_current_user, None)
    try:
        with patch("app.services.auth_service.PassClient") as MockPassClient:
            mock_pass = AsyncMock()
            mock_pass.me = AsyncMock(side_effect=UnauthorizedException(message="令牌无效或已过期"))
            MockPassClient.return_value = mock_pass

            resp = await client.get("/v1/auth/me")
        assert resp.status_code == 401
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user] = original


@pytest.mark.asyncio
async def test_forgot_password_returns_410(client: AsyncClient):
    """Deprecated endpoint should return 410 Gone."""
    resp = await client.post("/v1/auth/forgot-password", json={"email": "x@x.com"})
    assert resp.status_code == 410


@pytest.mark.asyncio
async def test_reset_password_returns_410(client: AsyncClient):
    """Deprecated endpoint should return 410 Gone."""
    resp = await client.post("/v1/auth/reset-password", json={"token": "x", "new_password": "y"})
    assert resp.status_code == 410
