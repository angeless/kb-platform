"""FastAPI dependency injection functions."""

import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, Header
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
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    authorization: str = Header(...),
) -> User:
    """Extract and verify JWT from Authorization header, then load user from DB."""
    if not authorization.startswith("Bearer "):
        raise UnauthorizedException(message="Invalid authorization header")

    token = authorization[len("Bearer "):]
    try:
        payload = decode_access_token(token, settings.jwt_secret, settings.jwt_algorithm)
    except Exception:
        raise UnauthorizedException(message="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException(message="Token missing subject")

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise UnauthorizedException(message="Invalid user ID in token")

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedException(message="User not found")

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
