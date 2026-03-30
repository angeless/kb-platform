"""Tests for login via PA Pass.

Verifies that:
1. Successful login calls PassClient.login() and returns token
2. First-time Pass login auto-creates KB Tenant + User
3. Repeat login finds existing User by pass_id
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from shared_errors import UnauthorizedException


def _make_auth_service():
    """Create an AuthService instance with mocked DB and PassClient."""
    from app.services.auth_service import AuthService

    settings = MagicMock()
    settings.pass_base_url = "http://mock-pass"
    settings.kb_product_id = "mock-product-id"

    svc = AuthService.__new__(AuthService)
    svc.db = AsyncMock()
    svc.settings = settings
    svc.db.flush = AsyncMock()
    svc.db.add = MagicMock()
    svc._pass = AsyncMock()
    return svc


class TestLoginViaPass:
    """Login delegates to Pass and auto-provisions KB User."""

    @pytest.mark.asyncio
    async def test_login_first_time_creates_user(self):
        svc = _make_auth_service()
        svc._pass.login = AsyncMock(return_value={
            "passId": "pass-uuid-789",
            "token": "pass-jwt-token",
            "expiresAt": "2026-03-29T12:00:00Z",
            "productBindings": [],
        })
        # No existing user
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        result = await svc.login("new@test.com", "Password1!")

        assert result["access_token"] == "pass-jwt-token"
        # Should have created Tenant + User
        assert svc.db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_login_existing_user_no_duplicate(self):
        svc = _make_auth_service()
        svc._pass.login = AsyncMock(return_value={
            "passId": "pass-uuid-existing",
            "token": "pass-jwt-token",
            "expiresAt": "2026-03-29T12:00:00Z",
            "productBindings": [],
        })
        existing_user = MagicMock()
        existing_user.id = uuid.uuid4()
        existing_user.kb_id = uuid.uuid4()
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_user))
        )

        result = await svc.login("existing@test.com", "Password1!")

        assert result["access_token"] == "pass-jwt-token"
        # Should NOT have created new Tenant or User
        svc.db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_login_pass_401_raises_unauthorized(self):
        svc = _make_auth_service()
        svc._pass.login = AsyncMock(side_effect=UnauthorizedException(
            error_code="AUTH_INVALID_CREDENTIALS",
            message="邮箱或密码错误",
        ))

        with pytest.raises(UnauthorizedException):
            await svc.login("wrong@test.com", "wrongpass")
