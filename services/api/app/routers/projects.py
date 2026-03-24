"""Projects router: CRUD endpoints with tenant isolation."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta
from shared_schemas.project import ProjectCreate, ProjectOut, ProjectUpdate

from app.deps import get_db, get_tenant_id, require_role
from shared_models import User
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
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ProjectService(db, tenant_id)
    project = await svc.create(name=body.name, industry_hint=body.industry_hint)
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
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ProjectService(db, tenant_id)
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
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ProjectService(db, tenant_id)
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
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ProjectService(db, tenant_id)
    project = await svc.update(
        project_id,
        name=body.name,
        industry_hint=body.industry_hint,
        status=body.status,
    )
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
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    _user: User = require_role("tenant_admin"),
):
    svc = ProjectService(db, tenant_id)
    await svc.delete(project_id)
    return DataResponse(data={"deleted": True})


@router.post(
    "/route",
    response_model=ListResponse,
    summary="Route content to best-matching projects",
    description="Given content keywords, returns top-3 candidate projects ranked by relevance.",
    responses={
        200: {"description": "Routing candidates returned"},
        **_RESP_AUTH,
    },
)
async def route_content(
    body: dict,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    from app.services.project_router_service import ProjectRouterService
    keywords = body.get("keywords", [])
    exclude_id = body.get("exclude_project_id")
    svc = ProjectRouterService(db, tenant_id)
    candidates = await svc.route(
        content_keywords=keywords,
        exclude_project_id=uuid.UUID(exclude_id) if exclude_id else None,
    )
    return ListResponse(
        data=candidates,
        meta=PaginationMeta(page=1, page_size=len(candidates), total=len(candidates)),
    )
