"""Audit log router: query audit records."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.audit import AuditLogOut
from shared_schemas.common import ErrorDetail, ListResponse, PaginationMeta

from app.deps import get_db, get_tenant_id, require_role
from app.services.audit_service import AuditService
from shared_models import User

router = APIRouter(prefix="/v1/audit-logs", tags=["audit"])


@router.get(
    "",
    response_model=ListResponse[AuditLogOut],
    summary="List audit logs",
    description="Returns a paginated list of audit log entries. Can be filtered by project, action, or resource type. Requires tenant_admin role.",
    responses={
        200: {"description": "Audit log list returned"},
        401: {"description": "Unauthorized", "model": ErrorDetail},
        403: {"description": "Forbidden — requires tenant_admin role", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def list_audit_logs(
    project_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = require_role("tenant_admin"),
):
    svc = AuditService(db, tenant_id, current_user.id)
    logs, total = await svc.list(
        project_id=project_id,
        action=action,
        resource_type=resource_type,
        page=page,
        page_size=page_size,
    )
    return ListResponse(
        data=[AuditLogOut.model_validate(log) for log in logs],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )
