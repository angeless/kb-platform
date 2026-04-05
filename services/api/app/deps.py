"""FastAPI dependency injection functions."""

import hashlib
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings, get_settings
from sqlalchemy import func as sa_func

from shared_errors import ErrorCode, ForbiddenException, UnauthorizedException
from shared_models import ApiKey, User

logger = logging.getLogger(__name__)
from shared_models.database import async_session_factory
from shared_models.tenant import Tenant

from .services.auth_service import AuthService


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
    """Extract Pass JWT from header or cookie, verify via Pass /me, load KB User.

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

    # Verify token via Pass /me and look up KB User
    svc = AuthService(db, settings)
    return await svc.verify_token(token)


async def get_kb_id(current_user: User = Depends(get_current_user)) -> uuid.UUID:
    """Return the tenant ID of the current user."""
    return current_user.kb_id


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


async def get_api_key_project(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> tuple[ApiKey, uuid.UUID, uuid.UUID]:
    """Authenticate via API key (Bearer token).

    Extracts the token from the Authorization header, SHA-256 hashes it,
    and looks up the corresponding active API key record.

    Returns (api_key_record, project_id, kb_id).
    """
    if not authorization:
        raise UnauthorizedException(
            error_code=ErrorCode.API_KEY_INVALID,
            message="未提供认证凭据",
        )
    if not authorization.startswith("Bearer "):
        raise UnauthorizedException(
            error_code=ErrorCode.API_KEY_INVALID,
            message="Authorization header must use Bearer scheme",
        )

    raw_key = authorization[len("Bearer "):]
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active.is_(True),
        )
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise UnauthorizedException(
            error_code=ErrorCode.API_KEY_INVALID,
            message="API Key 无效或已被撤销",
        )

    # Update last_used_at
    api_key.last_used_at = datetime.now(timezone.utc)
    await db.flush()

    return api_key, api_key.project_id, api_key.kb_id


# --- Tenant quota / feature gate dependencies (v0.52.5 — Gap-5 fix) ---


def check_quota(resource: str):
    """Factory that returns a dependency enforcing tenant quota for a resource.

    Supported resources: "projects", "users".
    """
    async def _check(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        tenant = await db.get(Tenant, current_user.kb_id)
        if tenant is None:
            logger.warning("check_quota(%s): no Tenant row for kb_id=%s — denying", resource, current_user.kb_id)
            raise ForbiddenException(
                error_code=ErrorCode.TENANT_QUOTA_EXCEEDED,
                message="租户初始化中，请稍后重试或联系管理员",
                detail={"reason": "tenant_not_found", "kb_id": str(current_user.kb_id)},
            )

        if resource == "projects" and tenant.quota_projects is not None:
            from shared_models.project import Project
            count = (await db.execute(
                select(sa_func.count()).where(Project.kb_id == tenant.id, Project.status != "deleted")
            )).scalar() or 0
            if count >= tenant.quota_projects:
                raise ForbiddenException(
                    error_code=ErrorCode.TENANT_QUOTA_EXCEEDED,
                    message=f"项目数量已达上限 ({tenant.quota_projects})",
                    detail={"resource": "projects", "limit": tenant.quota_projects, "current": count},
                )
        elif resource == "users" and tenant.quota_users is not None:
            count = (await db.execute(
                select(sa_func.count()).where(User.kb_id == tenant.id, User.status != "deleted")
            )).scalar() or 0
            if count >= tenant.quota_users:
                raise ForbiddenException(
                    error_code=ErrorCode.TENANT_QUOTA_EXCEEDED,
                    message=f"用户数量已达上限 ({tenant.quota_users})",
                    detail={"resource": "users", "limit": tenant.quota_users, "current": count},
                )

    return Depends(_check)


def check_feature(feature_name: str):
    """Factory that returns a dependency checking if a feature is enabled for the tenant.

    Checks tenant.feature_flags JSONB — e.g. {"advanced_search": true, "api_access": true}.
    """
    async def _check(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        tenant = await db.get(Tenant, current_user.kb_id)
        if tenant is None:
            logger.warning("check_feature(%s): no Tenant row for kb_id=%s — denying", feature_name, current_user.kb_id)
            raise ForbiddenException(
                error_code=ErrorCode.TENANT_FEATURE_DISABLED,
                message="租户初始化中，请稍后重试或联系管理员",
                detail={"reason": "tenant_not_found", "kb_id": str(current_user.kb_id)},
            )
        flags = tenant.feature_flags or {}
        if not flags.get(feature_name, False):
            raise ForbiddenException(
                error_code=ErrorCode.TENANT_FEATURE_DISABLED,
                message=f"当前套餐不支持「{feature_name}」功能",
                detail={"feature": feature_name, "tier": tenant.tier},
            )

    return Depends(_check)
