"""Tests for T-37-01: Registration transaction atomicity.

Verifies that:
1. Email check happens before any Tenant/User creation
2. Duplicate email registration returns 409 without creating a Tenant
3. Normal registration creates both Tenant and User
"""

import inspect
import re
import uuid
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from shared_errors import ConflictException


def _make_auth_service():
    """Create an AuthService instance with mocked DB."""
    from app.services.auth_service import AuthService

    settings = MagicMock()
    settings.jwt_secret = "test-secret"
    settings.jwt_algorithm = "HS256"

    svc = AuthService.__new__(AuthService)
    svc.db = AsyncMock()
    svc.settings = settings
    svc.db.flush = AsyncMock()
    svc.db.add = MagicMock()
    return svc


class TestRegisterEmailCheckBeforeFlush:
    """Email duplicate check must happen before Tenant creation."""

    def test_source_code_checks_email_before_tenant_creation(self):
        """Verify in source: email query appears before Tenant() instantiation."""
        from app.services.auth_service import AuthService

        source = inspect.getsource(AuthService.register)

        # Find positions of key operations
        email_check_pos = source.find("User.email == email")
        tenant_create_pos = source.find("Tenant(")

        assert email_check_pos != -1, "Email check not found in register()"
        assert tenant_create_pos != -1, "Tenant creation not found in register()"
        assert email_check_pos < tenant_create_pos, (
            "Email check must appear before Tenant creation in source code"
        )

    def test_source_code_raises_conflict_before_tenant(self):
        """ConflictException must be raised before Tenant is created."""
        from app.services.auth_service import AuthService

        source = inspect.getsource(AuthService.register)

        conflict_pos = source.find("ConflictException")
        tenant_pos = source.find("Tenant(")

        assert conflict_pos < tenant_pos


class TestRegisterDuplicateEmail:
    """Duplicate email must return 409 without creating Tenant."""

    @pytest.mark.asyncio
    async def test_duplicate_email_raises_409_no_tenant_created(self):
        svc = _make_auth_service()

        # Mock: email already exists
        existing_user = MagicMock()
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_user))
        )

        with pytest.raises(ConflictException) as exc_info:
            await svc.register("New Tenant", "existing@test.com", "password123")

        assert exc_info.value.error_code == "AUTH_EMAIL_ALREADY_EXISTS"
        # db.add should NOT have been called (no Tenant or User created)
        svc.db.add.assert_not_called()
        # flush should NOT have been called
        svc.db.flush.assert_not_called()


class TestRegisterSuccess:
    """Normal registration creates both Tenant and User."""

    @pytest.mark.asyncio
    async def test_normal_register_creates_tenant_and_user(self):
        svc = _make_auth_service()

        # Mock: email does not exist
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        result = await svc.register("Test Tenant", "new@test.com", "password123")

        assert "tenant_id" in result
        assert "user_id" in result
        assert result["email"] == "new@test.com"
        # db.add should have been called twice (Tenant + User)
        assert svc.db.add.call_count == 2
        # flush should have been called twice
        assert svc.db.flush.call_count == 2

    @pytest.mark.asyncio
    async def test_register_user_has_tenant_admin_role(self):
        svc = _make_auth_service()

        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        await svc.register("My Org", "admin@org.com", "securepass")

        # Second add call should be the User
        user_arg = svc.db.add.call_args_list[1][0][0]
        assert user_arg.role == "tenant_admin"
        assert user_arg.status == "active"
