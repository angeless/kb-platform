"""API Key management router: create, list, and revoke API keys for projects."""

import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ErrorCode, NotFoundException
from shared_models import ApiKey, User
from shared_schemas.api_key import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyListItem
from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta

from app.deps import get_current_user, get_db

router = APIRouter(prefix="/v1/projects/{project_id}/api-keys", tags=["api-keys"])

_RESP_AUTH = {
    401: {"description": "Unauthorized", "model": ErrorDetail},
    403: {"description": "Forbidden", "model": ErrorDetail},
}


@router.post(
    "",
    response_model=DataResponse[ApiKeyCreateResponse],
    summary="Create an API key for a project",
    description="Generates a new API key. The raw key is returned only once — store it securely.",
    responses={200: {"description": "API key created"}, **_RESP_AUTH},
)
async def create_api_key(
    project_id: uuid.UUID,
    body: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    raw_key = "kb_" + secrets.token_urlsafe(24)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:8]

    api_key = ApiKey(
        project_id=project_id,
        tenant_id=current_user.tenant_id,
        name=body.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        is_active=True,
        created_by=current_user.id,
    )
    db.add(api_key)
    await db.flush()

    return DataResponse(
        data=ApiKeyCreateResponse(
            id=api_key.id,
            name=api_key.name,
            key_prefix=key_prefix,
            raw_key=raw_key,
            created_at=api_key.created_at,
        )
    )


@router.get(
    "",
    response_model=ListResponse[ApiKeyListItem],
    summary="List API keys for a project",
    description="Returns all API keys for the project. The raw key is never returned.",
    responses={200: {"description": "API keys listed"}, **_RESP_AUTH},
)
async def list_api_keys(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(ApiKey)
        .where(
            ApiKey.project_id == project_id,
            ApiKey.tenant_id == current_user.tenant_id,
        )
        .order_by(ApiKey.created_at.desc())
    )
    result = await db.execute(q)
    keys = result.scalars().all()

    items = [ApiKeyListItem.model_validate(k) for k in keys]
    return ListResponse(
        data=items,
        meta=PaginationMeta(page=1, page_size=len(items), total=len(items)),
    )


@router.delete(
    "/{key_id}",
    response_model=DataResponse[dict],
    summary="Revoke an API key",
    description="Deactivates an API key. It can no longer be used for authentication.",
    responses={200: {"description": "API key revoked"}, **_RESP_AUTH},
)
async def revoke_api_key(
    project_id: uuid.UUID,
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(ApiKey).where(
        ApiKey.id == key_id,
        ApiKey.project_id == project_id,
        ApiKey.tenant_id == current_user.tenant_id,
    )
    result = await db.execute(q)
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise NotFoundException(
            error_code=ErrorCode.ASSET_NOT_FOUND,
            message="API Key 不存在",
        )

    api_key.is_active = False
    await db.flush()

    return DataResponse(data={"revoked": True, "key_id": str(key_id)})
