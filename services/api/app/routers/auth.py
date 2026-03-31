"""Auth router: register, login, refresh, logout, me."""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_errors import UnauthorizedException
from shared_models import User
from shared_schemas.auth import LoginRequest, RegisterRequest
from shared_schemas.common import DataResponse, ErrorDetail

from app.deps import get_current_user, get_db, get_settings_dep
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _is_secure(settings: Settings) -> bool:
    """Determine if cookies should use Secure flag based on environment."""
    cors = getattr(settings, "cors_origins", "")
    return "localhost" not in cors and "127.0.0.1" not in cors


def _set_access_cookie(
    response: JSONResponse,
    token: str,
    expires_at: str | None,
    settings: Settings,
) -> None:
    """Set httpOnly cookie for the Pass access token."""
    secure = _is_secure(settings)
    # Calculate max_age from expiresAt if available, else default 1 hour
    max_age = 3600
    if expires_at:
        try:
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            remaining = (exp_dt - datetime.now(timezone.utc)).total_seconds()
            if remaining > 0:
                max_age = int(remaining)
        except (ValueError, TypeError) as e:
            logger.warning("Could not parse Pass expiresAt '%s': %s — defaulting to 3600s", expires_at, e)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
        max_age=max_age,
    )


@router.post(
    "/register",
    response_model=DataResponse,
    status_code=201,
    summary="Register via PA Pass and create KB account",
    responses={
        201: {"description": "Registered and logged in"},
        409: {"description": "Email already registered", "model": ErrorDetail},
        422: {"description": "Validation error"},
        502: {"description": "Pass service unavailable", "model": ErrorDetail},
    },
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    svc = AuthService(db, settings)
    result = await svc.register(body.email, body.password, body.display_name or "")
    response = JSONResponse(
        content={"data": result},
        status_code=201,
    )
    _set_access_cookie(response, result["access_token"], result.get("expires_at"), settings)
    return response


@router.post(
    "/login",
    response_model=DataResponse,
    summary="Login via PA Pass",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials", "model": ErrorDetail},
        403: {"description": "Account banned", "model": ErrorDetail},
        502: {"description": "Pass service unavailable", "model": ErrorDetail},
    },
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    svc = AuthService(db, settings)
    result = await svc.login(body.email, body.password)
    response = JSONResponse(content={"data": result})
    _set_access_cookie(response, result["access_token"], result.get("expires_at"), settings)
    return response


@router.post(
    "/refresh",
    response_model=DataResponse,
    summary="Refresh Pass token",
    responses={
        200: {"description": "New token returned"},
        401: {"description": "Token invalid or expired", "model": ErrorDetail},
        502: {"description": "Pass service unavailable", "model": ErrorDetail},
    },
)
async def refresh(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    # Get current token from cookie or header
    token = request.cookies.get("access_token")
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]

    if not token:
        raise UnauthorizedException(message="未提供认证凭据")

    svc = AuthService(db, settings)
    result = await svc.refresh(token)
    response = JSONResponse(content={"data": result})
    _set_access_cookie(response, result["access_token"], result.get("expires_at"), settings)
    return response


@router.post(
    "/logout",
    status_code=204,
    summary="User logout",
    description="Clears authentication cookies. Pass token invalidation is handled by PA platform.",
    responses={
        204: {"description": "Logged out, cookies cleared"},
        401: {"description": "Unauthorized", "model": ErrorDetail},
    },
)
async def logout(request: Request, settings: Settings = Depends(get_settings_dep)):
    secure = _is_secure(settings)
    response = JSONResponse(content=None, status_code=204)
    response.delete_cookie(key="access_token", path="/", secure=secure, samesite="lax")
    return response


@router.get(
    "/me",
    response_model=DataResponse,
    summary="Get current user info",
    responses={
        200: {"description": "User info returned"},
        401: {"description": "Not authenticated", "model": ErrorDetail},
    },
)
async def me(current_user: User = Depends(get_current_user)):
    return DataResponse(
        data={
            "id": str(current_user.id),
            "email": current_user.email,
            "role": current_user.role,
            "kb_id": str(current_user.kb_id),
        }
    )


# Deprecated endpoints — password management is now handled by PA Pass
@router.post("/forgot-password", status_code=410, include_in_schema=False)
async def forgot_password():
    return JSONResponse(
        status_code=410,
        content={"message": "密码管理已迁移至 PA 平台，请通过 PA 平台重置密码"},
    )


@router.post("/reset-password", status_code=410, include_in_schema=False)
async def reset_password():
    return JSONResponse(
        status_code=410,
        content={"message": "密码管理已迁移至 PA 平台，请通过 PA 平台重置密码"},
    )
