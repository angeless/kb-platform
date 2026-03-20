"""Tests for T-36-06: User self-deletion and last-admin protection.

Verifies that delete() prevents:
1. Users from deleting themselves
2. Deleting the last admin of a tenant
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from shared_errors import ConflictException, ForbiddenException


def _make_user_service(tenant_id: uuid.UUID | None = None):
    """Create a UserService instance with mocked DB."""
    from app.services.user_service import UserService

    tid = tenant_id or uuid.uuid4()
    svc = UserService.__new__(UserService)
    svc.db = AsyncMock()
    svc.tenant_id = tid
    svc.db.flush = AsyncMock()
    svc.db.refresh = AsyncMock()
    return svc


class TestSelfDeletionProtection:
    """Users cannot delete their own account."""

    @pytest.mark.asyncio
    async def test_admin_delete_self_raises_403(self):
        svc = _make_user_service()
        user_id = uuid.uuid4()
        with pytest.raises(ForbiddenException) as exc_info:
            await svc.delete(user_id, operator_id=user_id)
        assert "不能删除自己的账号" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_delete_other_user_succeeds(self):
        svc = _make_user_service()
        operator_id = uuid.uuid4()
        target_id = uuid.uuid4()

        target_user = MagicMock()
        target_user.id = target_id
        target_user.role = "editor"
        target_user.status = "active"

        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=target_user))
        )
        result = await svc.delete(target_id, operator_id=operator_id)
        assert result.status == "disabled"


class TestLastAdminProtection:
    """Cannot delete the last admin of a tenant."""

    @pytest.mark.asyncio
    async def test_delete_sole_admin_raises_409(self):
        svc = _make_user_service()
        operator_id = uuid.uuid4()
        admin_id = uuid.uuid4()

        admin_user = MagicMock()
        admin_user.id = admin_id
        admin_user.role = "tenant_admin"
        admin_user.status = "active"

        # First call: find user; Second call: count admins (returns 1)
        svc.db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=admin_user)),
            MagicMock(scalar_one=MagicMock(return_value=1)),
        ])

        with pytest.raises(ConflictException) as exc_info:
            await svc.delete(admin_id, operator_id=operator_id)
        assert "不能删除租户唯一管理员" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_delete_non_sole_admin_succeeds(self):
        svc = _make_user_service()
        operator_id = uuid.uuid4()
        admin_id = uuid.uuid4()

        admin_user = MagicMock()
        admin_user.id = admin_id
        admin_user.role = "tenant_admin"
        admin_user.status = "active"

        # First call: find user; Second call: count admins (returns 2)
        svc.db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=admin_user)),
            MagicMock(scalar_one=MagicMock(return_value=2)),
        ])

        result = await svc.delete(admin_id, operator_id=operator_id)
        assert result.status == "disabled"

    @pytest.mark.asyncio
    async def test_delete_regular_user_no_admin_check(self):
        """Deleting a non-admin user should not trigger admin count check."""
        svc = _make_user_service()
        operator_id = uuid.uuid4()
        target_id = uuid.uuid4()

        target_user = MagicMock()
        target_user.id = target_id
        target_user.role = "viewer"
        target_user.status = "active"

        # Only one DB call expected: find user (no admin count query)
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=target_user))
        )
        result = await svc.delete(target_id, operator_id=operator_id)
        assert result.status == "disabled"
        # Verify execute was called only once (no admin count query)
        assert svc.db.execute.call_count == 1
