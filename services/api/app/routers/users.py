"""Users router: list, invite, update, delete endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ListResponse, PaginationMeta
from shared_schemas.user import UserInviteRequest, UserOut, UserUpdate

from app.deps import get_db, get_tenant_id, require_role
from app.services.user_service import UserService
from shared_models import User

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.get("", response_model=ListResponse[UserOut])
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = UserService(db, tenant_id)
    users, total = await svc.list(page=page, page_size=page_size)
    return ListResponse(
        data=[UserOut.model_validate(u) for u in users],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@router.post("/invite", response_model=DataResponse[UserOut], status_code=201)
async def invite_user(
    body: UserInviteRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    _user: User = require_role("tenant_admin"),
):
    svc = UserService(db, tenant_id)
    user = await svc.invite(email=body.email, role=body.role)
    return DataResponse(data=UserOut.model_validate(user))


@router.patch("/{user_id}", response_model=DataResponse[UserOut])
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    _user: User = require_role("tenant_admin"),
):
    svc = UserService(db, tenant_id)
    user = await svc.update(user_id, role=body.role, status=body.status)
    return DataResponse(data=UserOut.model_validate(user))


@router.delete("/{user_id}", response_model=DataResponse[UserOut])
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    _user: User = require_role("tenant_admin"),
):
    svc = UserService(db, tenant_id)
    user = await svc.delete(user_id)
    return DataResponse(data=UserOut.model_validate(user))
