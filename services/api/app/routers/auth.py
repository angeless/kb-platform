"""Auth router: register, login, refresh, logout, me."""

from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_errors import UnauthorizedException
from shared_models import User
from shared_schemas.auth import ForgotPasswordRequest, LoginRequest, RefreshRequest, RegisterRequest, ResetPasswordRequest
from shared_schemas.common import DataResponse, ErrorDetail

from app.deps import get_current_user, get_db, get_settings_dep
from app.services.auth_service import AuthService

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _is_secure(settings: Settings) -> bool:
    """Determine if cookies should use Secure flag based on environment."""
    cors = getattr(settings, "cors_origins", "")
    return "localhost" not in cors and "127.0.0.1" not in cors


def _set_token_cookies(
    response: JSONResponse,
    access_token: str,
    refresh_token: str | None,
    settings: Settings,
) -> None:
    """Set httpOnly cookies for access_token and optionally refresh_token."""
    secure = _is_secure(settings)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
        max_age=settings.access_token_expire_minutes * 60,
    )
    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/v1/auth",
            max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        )


@router.post(
    "/register",
    response_model=DataResponse,
    status_code=201,
    summary="Register a new tenant and admin user",
    description="Creates a new tenant organization and its first admin user.",
    responses={
        201: {"description": "Tenant and user created successfully"},
        409: {"description": "Email already registered", "model": ErrorDetail},
        422: {"description": "Validation error — invalid email or password format"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    svc = AuthService(db, settings)
    result = await svc.register(body.tenant_name, body.email, body.password)
    return DataResponse(data=result)


@router.post(
    "/login",
    response_model=DataResponse,
    summary="User login",
    description="Authenticates a user with email and password. Returns access and refresh JWT tokens, also sets httpOnly cookies.",
    responses={
        200: {"description": "Login successful, tokens returned"},
        401: {"description": "Invalid email or password", "model": ErrorDetail},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
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
    _set_token_cookies(response, result["access_token"], result["refresh_token"], settings)
    return response


@router.post(
    "/refresh",
    response_model=DataResponse,
    summary="Refresh access token",
    description="Exchanges a valid refresh token for a new access token. Accepts refresh_token in body or from httpOnly cookie.",
    responses={
        200: {"description": "New access token returned"},
        401: {"description": "Invalid or expired refresh token", "model": ErrorDetail},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def refresh(
    request: Request,
    body: Optional[RefreshRequest] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    # Priority: body > cookie
    refresh_token = None
    if body and body.refresh_token:
        refresh_token = body.refresh_token
    else:
        refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise UnauthorizedException(message="未提供刷新令牌")

    svc = AuthService(db, settings)
    result = await svc.refresh(refresh_token)
    response = JSONResponse(content={"data": result})
    _set_token_cookies(response, result["access_token"], None, settings)
    return response


@router.post(
    "/forgot-password",
    response_model=DataResponse,
    summary="Request password reset",
    description="Generates a password reset token. Always returns 200 regardless of email existence (prevents user enumeration).",
    responses={
        200: {"description": "Reset request processed"},
        422: {"description": "Validation error"},
    },
)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    svc = AuthService(db, settings)
    result = await svc.forgot_password(body.email)
    return DataResponse(data=result)


@router.post(
    "/reset-password",
    response_model=DataResponse,
    summary="Reset password with token",
    description="Resets the user's password using a valid reset token. Token is single-use and expires after 1 hour.",
    responses={
        200: {"description": "Password reset successful"},
        400: {"description": "Invalid or expired reset token", "model": ErrorDetail},
        422: {"description": "Validation error"},
    },
)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    svc = AuthService(db, settings)
    result = await svc.reset_password(body.token, body.new_password)
    return DataResponse(data=result)


@router.post(
    "/logout",
    status_code=204,
    summary="User logout",
    description="Revokes the current refresh token and clears authentication cookies.",
    responses={
        204: {"description": "Logged out, token revoked, cookies cleared"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    # Revoke refresh token in DB (best-effort: if no token found, still clear cookies)
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        svc = AuthService(db, settings)
        await svc.revoke_refresh_token(refresh_token)

    secure = _is_secure(settings)
    response = JSONResponse(content=None, status_code=204)
    response.delete_cookie(key="access_token", path="/", secure=secure, samesite="lax")
    response.delete_cookie(key="refresh_token", path="/v1/auth", secure=secure, samesite="lax")
    return response


@router.get(
    "/me",
    response_model=DataResponse,
    summary="Get current user info",
    description="Returns the current authenticated user's info. Used by frontend to restore session on page refresh.",
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
            "tenant_id": str(current_user.tenant_id),
        }
    )
