"""User service: list, invite, update, delete with tenant isolation."""

import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ConflictException, ErrorCode, NotFoundException
from shared_models import User

from app.utils.security import hash_password


class UserService:
    """Operations for users, scoped to a single tenant."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def list(self, page: int = 1, page_size: int = 20) -> tuple[list[User], int]:
        """Return paginated users for the tenant."""
        base = select(User).where(User.tenant_id == self.tenant_id)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = base.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()

        return list(rows), total

    async def invite(self, email: str, role: str = "viewer") -> User:
        """Invite a user by creating a record with a random temporary password."""
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
            tenant_id=self.tenant_id,
            email=email,
            password_hash=hash_password(temp_password),
            role=role,
            status="active",
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update(self, user_id: uuid.UUID, **kwargs) -> User:
        """Update user fields (role, status)."""
        q = select(User).where(
            User.id == user_id,
            User.tenant_id == self.tenant_id,
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

    async def delete(self, user_id: uuid.UUID) -> User:
        """Soft-delete user by setting status to 'disabled'."""
        q = select(User).where(
            User.id == user_id,
            User.tenant_id == self.tenant_id,
        )
        result = await self.db.execute(q)
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundException(
                error_code=ErrorCode.USER_NOT_FOUND,
                message="用户不存在",
            )
        user.status = "disabled"
        await self.db.flush()
        await self.db.refresh(user)
        return user
