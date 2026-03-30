"""Tests for T-36-05: User role escalation prevention.

Verifies that invite() and update() enforce operator role ceiling:
operators cannot assign roles higher than their own.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from shared_errors import ForbiddenException


def _make_user_service(kb_id: uuid.UUID | None = None):
    """Create a UserService instance with mocked DB."""
    from app.services.user_service import UserService

    tid = kb_id or uuid.uuid4()
    svc = UserService.__new__(UserService)
    svc.db = AsyncMock()
    svc.kb_id = tid
    svc.db.flush = AsyncMock()
    svc.db.refresh = AsyncMock()
    svc.db.add = MagicMock()
    return svc


class TestInviteRoleEscalation:
    """invite() must block escalation to roles above operator."""

    @pytest.mark.asyncio
    async def test_editor_invite_tenant_admin_raises_403(self):
        svc = _make_user_service()
        # Mock: no duplicate email
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        with pytest.raises(ForbiddenException) as exc_info:
            await svc.invite(email="new@test.com", role="tenant_admin", operator_role="editor")
        assert "不能邀请角色高于自身的用户" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_tenant_admin_invite_editor_succeeds(self):
        svc = _make_user_service()
        # Mock: no duplicate email
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        user = await svc.invite(email="new@test.com", role="editor", operator_role="tenant_admin")
        assert user.role == "editor"

    @pytest.mark.asyncio
    async def test_editor_invite_editor_succeeds(self):
        """Same-level invitation should succeed."""
        svc = _make_user_service()
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        user = await svc.invite(email="peer@test.com", role="editor", operator_role="editor")
        assert user.role == "editor"

    @pytest.mark.asyncio
    async def test_viewer_invite_editor_raises_403(self):
        svc = _make_user_service()
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        with pytest.raises(ForbiddenException):
            await svc.invite(email="x@test.com", role="editor", operator_role="viewer")

    @pytest.mark.asyncio
    async def test_tenant_admin_invite_platform_admin_raises_403(self):
        svc = _make_user_service()
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        with pytest.raises(ForbiddenException):
            await svc.invite(email="x@test.com", role="platform_admin", operator_role="tenant_admin")


class TestUpdateRoleEscalation:
    """update() must block setting role above operator's own role."""

    @pytest.mark.asyncio
    async def test_editor_set_viewer_to_tenant_admin_raises_403(self):
        svc = _make_user_service()
        with pytest.raises(ForbiddenException) as exc_info:
            await svc.update(uuid.uuid4(), operator_role="editor", role="tenant_admin")
        assert "不能将用户角色提升到高于自身的级别" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_tenant_admin_set_editor_to_reviewer_succeeds(self):
        svc = _make_user_service()
        target_user = MagicMock()
        target_user.id = uuid.uuid4()
        target_user.role = "editor"
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=target_user))
        )
        result = await svc.update(target_user.id, operator_role="tenant_admin", role="reviewer")
        assert result.role == "reviewer"

    @pytest.mark.asyncio
    async def test_update_status_only_no_role_check(self):
        """When updating only status (no role), role escalation check should not trigger."""
        svc = _make_user_service()
        target_user = MagicMock()
        target_user.id = uuid.uuid4()
        target_user.role = "editor"
        target_user.status = "active"
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=target_user))
        )
        # operator_role="viewer" but only changing status, not role — should succeed
        result = await svc.update(target_user.id, operator_role="viewer", status="disabled")
        assert result.status == "disabled"

    @pytest.mark.asyncio
    async def test_update_role_none_skips_check(self):
        """Passing role=None should not trigger escalation check."""
        svc = _make_user_service()
        target_user = MagicMock()
        target_user.id = uuid.uuid4()
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=target_user))
        )
        # role=None means no role change
        result = await svc.update(target_user.id, operator_role="editor", role=None, status="active")
        # Should not raise
        assert result is not None
