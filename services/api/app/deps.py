"""FastAPI dependency injection functions."""

import uuid
from collections.abc import AsyncGenerator
from typing import Optional

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings, get_settings
from shared_errors import ForbiddenException, UnauthorizedException
from shared_models import User
from shared_models.database import async_session_factory

from .utils.security import decode_access_token


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_settings_dep() -> Settings:
    """Return application settings."""
    return get_settings()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    authorization: Optional[str] = Header(None),
) -> User:
    """Extract and verify JWT from Authorization header or httpOnly cookie, then load user from DB.

    Priority: Authorization header > access_token cookie.
    """
    token: str | None = None

    # 1. Try Authorization header first
    if authorization and authorization.startswith("Bearer "):
        token = authorization[len("Bearer "):]
    elif authorization:
        raise UnauthorizedException(message="认证头格式错误")

    # 2. Fall back to httpOnly cookie
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise UnauthorizedException(message="未提供认证凭据")

    try:
        payload = decode_access_token(token, settings.jwt_secret, settings.jwt_algorithm)
    except Exception:
        raise UnauthorizedException(message="令牌无效或已过期")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException(message="令牌缺少用户标识")

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise UnauthorizedException(message="令牌中用户 ID 无效")

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedException(message="用户不存在")

    return user


async def get_tenant_id(current_user: User = Depends(get_current_user)) -> uuid.UUID:
    """Return the tenant ID of the current user."""
    return current_user.tenant_id


# Role hierarchy: higher number = more permissions
ROLE_HIERARCHY: dict[str, int] = {
    "viewer": 0,
    "editor": 1,
    "reviewer": 2,
    "project_admin": 3,
    "tenant_admin": 4,
    "admin": 4,  # legacy alias for tenant_admin
    "platform_admin": 5,
}


def require_role(minimum_role: str):
    """Factory that returns a FastAPI dependency enforcing a minimum role level."""

    async def _check(current_user: User = Depends(get_current_user)) -> User:
        user_level = ROLE_HIERARCHY.get(current_user.role, -1)
        required_level = ROLE_HIERARCHY.get(minimum_role, 99)
        if user_level < required_level:
            raise ForbiddenException(
                message=f"需要 {minimum_role} 或更高权限",
                detail={"current_role": current_user.role, "required_role": minimum_role},
            )
        return current_user

    return Depends(_check)
