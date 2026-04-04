"""Projects router: CRUD endpoints with tenant isolation."""

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta
from shared_schemas.cross_reference import RouteContentRequest
from shared_schemas.project import ProjectCreate, ProjectOut, ProjectUpdate

from app.deps import check_quota, get_current_user, get_db, get_kb_id, require_role
from shared_models import User
from app.services.audit_service import AuditService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/v1/projects", tags=["projects"])

_RESP_AUTH = {
    401: {"description": "Unauthorized", "model": ErrorDetail},
    403: {"description": "Forbidden", "model": ErrorDetail},
}


@router.post(
    "",
    response_model=DataResponse[ProjectOut],
    status_code=201,
    summary="Create a project",
    description="Creates a new knowledge project under the current tenant. The project serves as the top-level container for assets, documents, and architectures.",
    responses={
        201: {"description": "Project created successfully"},
        **_RESP_AUTH,
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    current_user: User = Depends(get_current_user),
    _quota=check_quota("projects"),
):
    svc = ProjectService(db, kb_id)
    project = await svc.create(name=body.name, industry_hint=body.industry_hint)
    audit = AuditService(db, kb_id, current_user.id)
    await audit.log("create_project", "project", project.id)
    return DataResponse(data=ProjectOut.model_validate(project))


@router.get(
    "",
    response_model=ListResponse[ProjectOut],
    summary="List projects",
    description="Returns a paginated list of projects for the current tenant.",
    responses={
        200: {"description": "Project list returned"},
        **_RESP_AUTH,
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
):
    svc = ProjectService(db, kb_id)
    projects, total = await svc.list(page=page, page_size=page_size)
    return ListResponse(
        data=[ProjectOut.model_validate(p) for p in projects],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@router.get(
    "/{project_id}",
    response_model=DataResponse[ProjectOut],
    summary="Get a project",
    description="Returns a single project by ID. The project must belong to the current tenant.",
    responses={
        200: {"description": "Project details returned"},
        **_RESP_AUTH,
        404: {"description": "Project not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
):
    svc = ProjectService(db, kb_id)
    project = await svc.get(project_id)
    return DataResponse(data=ProjectOut.model_validate(project))


@router.patch(
    "/{project_id}",
    response_model=DataResponse[ProjectOut],
    summary="Update a project",
    description="Partially updates a project's name, industry_hint, or status. Only provided fields are updated.",
    responses={
        200: {"description": "Project updated"},
        **_RESP_AUTH,
        404: {"description": "Project not found", "model": ErrorDetail},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db, kb_id)
    project = await svc.update(
        project_id,
        name=body.name,
        industry_hint=body.industry_hint,
        status=body.status,
    )
    audit = AuditService(db, kb_id, current_user.id)
    await audit.log("update_project", "project", project_id, project_id=project_id)
    return DataResponse(data=ProjectOut.model_validate(project))


@router.delete(
    "/{project_id}",
    response_model=DataResponse,
    summary="Delete a project",
    description="Soft-deletes a project. Requires tenant_admin role.",
    responses={
        200: {"description": "Project deleted"},
        **_RESP_AUTH,
        404: {"description": "Project not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def delete_project(
    project_id: uuid.UUID,
    confirmation_id: str | None = Query(None),
    code: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    current_user: User = require_role("tenant_admin"),
):
    # Confirmation code gate (v0.52.9 — Gap-7 fix)
    from app.utils.confirmation import generate_confirmation, verify_confirmation
    if not confirmation_id or not code:
        conf = generate_confirmation("delete_project", str(current_user.id))
        return JSONResponse(status_code=428, content={
            "error": "CONFIRMATION_REQUIRED",
            "message": "此操作需要确认码",
            "confirmation_id": conf["confirmation_id"],
            "code": conf["code"],
            "expires_in": conf["expires_in"],
        })
    if not verify_confirmation(confirmation_id, code, str(current_user.id)):
        return JSONResponse(status_code=403, content={"error": "CONFIRMATION_INVALID", "message": "确认码无效或已过期"})

    svc = ProjectService(db, kb_id)
    await svc.delete(project_id)
    audit = AuditService(db, kb_id, current_user.id)
    await audit.log("delete_project", "project", project_id, project_id=project_id)
    return DataResponse(data={"deleted": True})


@router.post(
    "/route",
    response_model=ListResponse,
    summary="Route content to best-matching projects",
    description="Layer 2 routing: embedding similarity + keyword overlap. Returns top-3 candidates with action (auto_route/recommend/low_confidence).",
    responses={
        200: {"description": "Routing candidates returned"},
        **_RESP_AUTH,
    },
)
async def route_content(
    body: RouteContentRequest,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
):
    from app.services.project_router_service import ProjectRouterService
    svc = ProjectRouterService(db, kb_id)
    candidates = await svc.route(
        content_embedding=body.embedding,
        content_keywords=body.keywords,
        exclude_project_id=body.exclude_project_id,
    )
    return ListResponse(
        data=candidates,
        meta=PaginationMeta(page=1, page_size=len(candidates), total=len(candidates)),
    )
