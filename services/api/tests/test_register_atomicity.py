"""Tests for registration via PA Pass.

Verifies that:
1. Register calls PassClient.register() and creates KB Tenant + User
2. Pass errors (409 conflict, etc.) are correctly propagated
3. Auto-provisioned user gets tenant_admin role
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared_errors import ConflictException


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


class TestRegisterViaPass:
    """Registration delegates to Pass and creates KB Tenant + User."""

    @pytest.mark.asyncio
    async def test_register_creates_tenant_and_user(self):
        svc = _make_auth_service()
        svc._pass.register = AsyncMock(return_value={
            "passId": "pass-uuid-123",
            "token": "pass-jwt-token",
            "expiresAt": "2026-03-29T12:00:00Z",
        })

        result = await svc.register("new@test.com", "Password1!", "My Name")

        assert "access_token" in result
        assert result["email"] == "new@test.com"
        # db.add should have been called twice (Tenant + User)
        assert svc.db.add.call_count == 2
        assert svc.db.flush.call_count == 2

    @pytest.mark.asyncio
    async def test_register_user_has_tenant_admin_role(self):
        svc = _make_auth_service()
        svc._pass.register = AsyncMock(return_value={
            "passId": "pass-uuid-456",
            "token": "pass-jwt-token",
            "expiresAt": "2026-03-29T12:00:00Z",
        })

        await svc.register("admin@org.com", "SecurePass1!", "Admin")

        # Second add call should be the User
        user_arg = svc.db.add.call_args_list[1][0][0]
        assert user_arg.role == "tenant_admin"
        assert user_arg.status == "active"
        assert user_arg.pass_id == "pass-uuid-456"
        assert user_arg.password_hash is None

    @pytest.mark.asyncio
    async def test_register_pass_conflict_raises_409(self):
        svc = _make_auth_service()
        svc._pass.register = AsyncMock(side_effect=ConflictException(
            error_code="AUTH_EMAIL_ALREADY_EXISTS",
            message="邮箱已注册",
        ))

        with pytest.raises(ConflictException) as exc_info:
            await svc.register("existing@test.com", "Password1!", "")

        assert exc_info.value.error_code == "AUTH_EMAIL_ALREADY_EXISTS"
        # No Tenant or User should have been created
        svc.db.add.assert_not_called()
