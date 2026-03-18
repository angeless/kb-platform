"""Auth router: register, login, refresh."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_schemas.auth import LoginRequest, RefreshRequest, RegisterRequest
from shared_schemas.common import DataResponse

from app.deps import get_db, get_settings_dep
from app.services.auth_service import AuthService

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/register", response_model=DataResponse, status_code=201)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    svc = AuthService(db, settings)
    result = await svc.register(body.tenant_name, body.email, body.password)
    return DataResponse(data=result)


@router.post("/login", response_model=DataResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    svc = AuthService(db, settings)
    result = await svc.login(body.email, body.password)
    return DataResponse(data=result)


@router.post("/refresh", response_model=DataResponse)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    svc = AuthService(db, settings)
    result = await svc.refresh(body.refresh_token)
    return DataResponse(data=result)
