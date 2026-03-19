"""Auth router: register, login, refresh."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_schemas.auth import LoginRequest, RefreshRequest, RegisterRequest
from shared_schemas.common import DataResponse, ErrorDetail

from app.deps import get_db, get_settings_dep
from app.services.auth_service import AuthService

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=DataResponse,
    status_code=201,
    summary="Register a new tenant and admin user",
    description="Creates a new tenant organization and its first admin user. Returns access and refresh tokens.",
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
    description="Authenticates a user with email and password. Returns access and refresh JWT tokens.",
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
    return DataResponse(data=result)


@router.post(
    "/refresh",
    response_model=DataResponse,
    summary="Refresh access token",
    description="Exchanges a valid refresh token for a new access token. The refresh token itself is not rotated.",
    responses={
        200: {"description": "New access token returned"},
        401: {"description": "Invalid or expired refresh token", "model": ErrorDetail},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    svc = AuthService(db, settings)
    result = await svc.refresh(body.refresh_token)
    return DataResponse(data=result)
