"""Conflicts router: list, get, resolve endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta
from shared_schemas.knowledge import ConflictOut, ConflictResolveRequest

from app.deps import get_current_user, get_db, get_tenant_id, require_role
from app.services.audit_service import AuditService
from app.services.conflict_service import ConflictService
from shared_models import User

router = APIRouter(prefix="/v1/conflicts", tags=["conflicts"])

_RESP_AUTH = {
    401: {"description": "Unauthorized", "model": ErrorDetail},
    403: {"description": "Forbidden", "model": ErrorDetail},
}


@router.get(
    "",
    response_model=ListResponse[ConflictOut],
    summary="List knowledge conflicts",
    description="Returns a paginated list of detected knowledge conflicts for a project.",
    responses={
        200: {"description": "Conflict list returned"},
        **_RESP_AUTH,
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def list_conflicts(
    project_id: uuid.UUID = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    svc = ConflictService(db, tenant_id, current_user.id)
    conflicts, total = await svc.list(project_id=project_id, page=page, page_size=page_size)
    return ListResponse(
        data=[ConflictOut.model_validate(c) for c in conflicts],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@router.get(
    "/pending",
    response_model=ListResponse[ConflictOut],
    summary="List pending conflicts",
    description="Returns a paginated list of unresolved knowledge conflicts for a project.",
    responses={
        200: {"description": "Pending conflict list returned"},
        **_RESP_AUTH,
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def list_pending_conflicts(
    project_id: uuid.UUID = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    svc = ConflictService(db, tenant_id, current_user.id)
    conflicts, total = await svc.list_pending(project_id=project_id, page=page, page_size=page_size)
    return ListResponse(
        data=[ConflictOut.model_validate(c) for c in conflicts],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@router.get(
    "/{conflict_id}",
    response_model=DataResponse[ConflictOut],
    summary="Get a conflict",
    description="Returns details of a single knowledge conflict, including the conflicting documents.",
    responses={
        200: {"description": "Conflict details returned"},
        **_RESP_AUTH,
        404: {"description": "Conflict not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def get_conflict(
    conflict_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    svc = ConflictService(db, tenant_id, current_user.id)
    conflict = await svc.get(conflict_id)
    return DataResponse(data=ConflictOut.model_validate(conflict))


@router.post(
    "/{conflict_id}/resolve",
    response_model=DataResponse[ConflictOut],
    summary="Resolve a conflict",
    description="Marks a knowledge conflict as resolved with a resolution note. Requires reviewer role.",
    responses={
        200: {"description": "Conflict resolved"},
        **_RESP_AUTH,
        404: {"description": "Conflict not found", "model": ErrorDetail},
        409: {"description": "Conflict already resolved", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def resolve_conflict(
    conflict_id: uuid.UUID,
    body: ConflictResolveRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = require_role("reviewer"),
):
    svc = ConflictService(db, tenant_id, current_user.id)
    conflict = await svc.resolve(conflict_id, body.resolution_note)
    audit = AuditService(db, tenant_id, current_user.id)
    await audit.log("resolve", "conflict", conflict_id, project_id=conflict.project_id)
    return DataResponse(data=ConflictOut.model_validate(conflict))
