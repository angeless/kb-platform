"""Users router: list, invite, update, delete endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta
from shared_schemas.user import UserInviteRequest, UserOut, UserUpdate

from app.deps import get_db, get_tenant_id, require_role
from app.services.user_service import UserService
from shared_models import User

router = APIRouter(prefix="/v1/users", tags=["users"])

_RESP_AUTH = {
    401: {"description": "Unauthorized", "model": ErrorDetail},
    403: {"description": "Forbidden", "model": ErrorDetail},
}


@router.get(
    "",
    response_model=ListResponse[UserOut],
    summary="List users",
    description="Returns a paginated list of users in the current tenant.",
    responses={
        200: {"description": "User list returned"},
        **_RESP_AUTH,
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
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


@router.post(
    "/invite",
    response_model=DataResponse[UserOut],
    status_code=201,
    summary="Invite a user",
    description="Invites a new user to the tenant with the specified role. Requires tenant_admin role.",
    responses={
        201: {"description": "User invited"},
        **_RESP_AUTH,
        409: {"description": "Email already exists in tenant", "model": ErrorDetail},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def invite_user(
    body: UserInviteRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    _user: User = require_role("tenant_admin"),
):
    svc = UserService(db, tenant_id)
    user = await svc.invite(email=body.email, role=body.role, operator_role=_user.role)
    return DataResponse(data=UserOut.model_validate(user))


@router.patch(
    "/{user_id}",
    response_model=DataResponse[UserOut],
    summary="Update a user",
    description="Updates a user's role or status. Requires tenant_admin role.",
    responses={
        200: {"description": "User updated"},
        **_RESP_AUTH,
        404: {"description": "User not found", "model": ErrorDetail},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    _user: User = require_role("tenant_admin"),
):
    svc = UserService(db, tenant_id)
    user = await svc.update(user_id, operator_role=_user.role, role=body.role, status=body.status)
    return DataResponse(data=UserOut.model_validate(user))


@router.delete(
    "/{user_id}",
    response_model=DataResponse[UserOut],
    summary="Delete a user",
    description="Soft-deletes a user from the tenant. Requires tenant_admin role.",
    responses={
        200: {"description": "User deleted"},
        **_RESP_AUTH,
        404: {"description": "User not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    _user: User = require_role("tenant_admin"),
):
    svc = UserService(db, tenant_id)
    user = await svc.delete(user_id, operator_id=_user.id)
    return DataResponse(data=UserOut.model_validate(user))
