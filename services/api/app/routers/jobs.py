"""Jobs router: CRUD endpoints with tenant isolation."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta
from shared_schemas.job import JobCreate, JobOut

from app.deps import get_current_user, get_db, get_tenant_id, require_role
from app.services.job_service import JobService
from shared_models import User

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])

_RESP_AUTH = {
    401: {"description": "Unauthorized", "model": ErrorDetail},
    403: {"description": "Forbidden", "model": ErrorDetail},
}


@router.post(
    "",
    response_model=DataResponse[JobOut],
    status_code=201,
    summary="Create a processing job",
    description="Creates a new async processing job (e.g., ingestion, pipeline, AI orchestration). The job is dispatched to a Celery worker.",
    responses={
        201: {"description": "Job created and queued"},
        **_RESP_AUTH,
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def create_job(
    body: JobCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = require_role("editor"),
):
    svc = JobService(db, tenant_id, current_user.id)
    job = await svc.create(project_id=body.project_id, job_type=body.job_type, asset_id=body.asset_id)
    return DataResponse(data=JobOut.model_validate(job))


@router.get(
    "",
    response_model=ListResponse[JobOut],
    summary="List jobs",
    description="Returns a paginated list of processing jobs for a given project.",
    responses={
        200: {"description": "Job list returned"},
        **_RESP_AUTH,
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
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


@router.get(
    "/{job_id}",
    response_model=DataResponse[JobOut],
    summary="Get a job",
    description="Returns details of a single processing job by ID, including its current status and progress.",
    responses={
        200: {"description": "Job details returned"},
        **_RESP_AUTH,
        404: {"description": "Job not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    svc = JobService(db, tenant_id, current_user.id)
    job = await svc.get(job_id)
    return DataResponse(data=JobOut.model_validate(job))


@router.post(
    "/{job_id}/retry",
    response_model=DataResponse[JobOut],
    summary="Retry a failed job",
    description="Re-queues a failed job for processing. Only jobs in 'failed' status can be retried.",
    responses={
        200: {"description": "Job re-queued for processing"},
        **_RESP_AUTH,
        404: {"description": "Job not found", "model": ErrorDetail},
        409: {"description": "Job is not in a retriable state", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def retry_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    svc = JobService(db, tenant_id, current_user.id)
    job = await svc.retry(job_id)
    return DataResponse(data=JobOut.model_validate(job))
