"""Jobs router: CRUD endpoints with tenant isolation."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ListResponse, PaginationMeta
from shared_schemas.job import JobCreate, JobOut

from app.deps import get_current_user, get_db, get_tenant_id
from app.services.job_service import JobService
from shared_models import User

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


@router.post("", response_model=DataResponse[JobOut], status_code=201)
async def create_job(
    body: JobCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    svc = JobService(db, tenant_id, current_user.id)
    job = await svc.create(project_id=body.project_id, job_type=body.job_type)
    return DataResponse(data=JobOut.model_validate(job))


@router.get("", response_model=ListResponse[JobOut])
async def list_jobs(
    project_id: uuid.UUID = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    svc = JobService(db, tenant_id, current_user.id)
    jobs, total = await svc.list(project_id=project_id, page=page, page_size=page_size)
    return ListResponse(
        data=[JobOut.model_validate(j) for j in jobs],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/{job_id}", response_model=DataResponse[JobOut])
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    svc = JobService(db, tenant_id, current_user.id)
    job = await svc.get(job_id)
    return DataResponse(data=JobOut.model_validate(job))


@router.post("/{job_id}/retry", response_model=DataResponse[JobOut])
async def retry_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    svc = JobService(db, tenant_id, current_user.id)
    job = await svc.retry(job_id)
    return DataResponse(data=JobOut.model_validate(job))
