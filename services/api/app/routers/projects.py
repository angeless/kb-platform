"""Projects router: CRUD endpoints with tenant isolation."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ListResponse, PaginationMeta
from shared_schemas.project import ProjectCreate, ProjectOut, ProjectUpdate

from app.deps import get_db, get_tenant_id, require_role
from shared_models import User
from app.services.project_service import ProjectService

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.post("", response_model=DataResponse[ProjectOut], status_code=201)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ProjectService(db, tenant_id)
    project = await svc.create(name=body.name, industry_hint=body.industry_hint)
    return DataResponse(data=ProjectOut.model_validate(project))


@router.get("", response_model=ListResponse[ProjectOut])
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


@router.get("/{project_id}", response_model=DataResponse[ProjectOut])
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ProjectService(db, tenant_id)
    project = await svc.get(project_id)
    return DataResponse(data=ProjectOut.model_validate(project))


@router.patch("/{project_id}", response_model=DataResponse[ProjectOut])
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


@router.delete("/{project_id}", response_model=DataResponse)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    _user: User = require_role("tenant_admin"),
):
    svc = ProjectService(db, tenant_id)
    await svc.delete(project_id)
    return DataResponse(data={"deleted": True})
