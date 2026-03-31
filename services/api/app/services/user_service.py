"""User service: list, invite, update, delete with tenant isolation."""

import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ConflictException, ErrorCode, ForbiddenException, NotFoundException
from shared_models import User

from app.deps import ROLE_HIERARCHY
from app.utils.security import hash_password


class UserService:
    """Operations for users, scoped to a single tenant."""

    def __init__(self, db: AsyncSession, kb_id: uuid.UUID) -> None:
        self.db = db
        self.kb_id = kb_id

    async def list(self, page: int = 1, page_size: int = 20) -> tuple[list[User], int]:
        """Return paginated users for the tenant."""
        base = select(User).where(User.kb_id == self.kb_id)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = base.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()

        return list(rows), total

    async def invite(self, email: str, role: str = "viewer", operator_role: str = "") -> User:
        """Invite a user by creating a record with a random temporary password."""
        # Check: operator cannot invite a user with a higher role than their own
        if operator_role and ROLE_HIERARCHY.get(role, 99) > ROLE_HIERARCHY.get(operator_role, -1):
            raise ForbiddenException(
                message="不能邀请角色高于自身的用户",
                detail={"operator_role": operator_role, "target_role": role},
            )

        # Check duplicate email
        dup_q = select(User).where(User.email == email)
        dup = (await self.db.execute(dup_q)).scalar_one_or_none()
        if dup is not None:
            raise ConflictException(
                error_code=ErrorCode.AUTH_EMAIL_ALREADY_EXISTS,
                message="邮箱已被使用",
            )

        temp_password = secrets.token_urlsafe(16)
        user = User(
            id=uuid.uuid4(),
            kb_id=self.kb_id,
            email=email,
            password_hash=hash_password(temp_password),
            role=role,
            status="active",
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update(self, user_id: uuid.UUID, operator_role: str = "", **kwargs) -> User:
        """Update user fields (role, status)."""
        # Check: operator cannot set a role higher than their own
        target_role = kwargs.get("role")
        if operator_role and target_role is not None and ROLE_HIERARCHY.get(target_role, 99) > ROLE_HIERARCHY.get(operator_role, -1):
            raise ForbiddenException(
                message="不能将用户角色提升到高于自身的级别",
                detail={"operator_role": operator_role, "target_role": target_role},
            )

        q = select(User).where(
            User.id == user_id,
            User.kb_id == self.kb_id,
        )
        result = await self.db.execute(q)
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundException(
                error_code=ErrorCode.USER_NOT_FOUND,
                message="用户不存在",
            )
        for key, value in kwargs.items():
            if value is not None:
                setattr(user, key, value)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user_id: uuid.UUID, operator_id: uuid.UUID | None = None) -> User:
        """Soft-delete user by setting status to 'disabled'."""
        # Rule 1: cannot delete yourself
        if operator_id is not None and user_id == operator_id:
            raise ForbiddenException(
                message="不能删除自己的账号",
            )

        q = select(User).where(
            User.id == user_id,
            User.kb_id == self.kb_id,
        )
        result = await self.db.execute(q)
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundException(
                error_code=ErrorCode.USER_NOT_FOUND,
                message="用户不存在",
            )

        # Rule 2: cannot delete the last admin of the tenant
        if user.role in ("tenant_admin", "admin"):
            admin_count_q = select(func.count()).select_from(
                select(User).where(
                    User.kb_id == self.kb_id,
                    User.role.in_(["tenant_admin", "admin"]),
                    User.status == "active",
                ).subquery()
            )
            admin_count = (await self.db.execute(admin_count_q)).scalar_one()
            if admin_count <= 1:
                raise ConflictException(
                    error_code=ErrorCode.AUTH_INSUFFICIENT_ROLE,
                    message="不能删除租户唯一管理员",
                )

        user.status = "disabled"
        await self.db.flush()
        await self.db.refresh(user)
        return user
