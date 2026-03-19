"""Ingestion router: incremental ingestion endpoint."""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ErrorDetail
from shared_schemas.job import JobOut

from app.deps import get_current_user, get_db, get_tenant_id
from app.services.job_service import JobService
from shared_models import User

router = APIRouter(prefix="/v1/ingestion", tags=["ingestion"])

_RESP_AUTH = {
    401: {"description": "Unauthorized", "model": ErrorDetail},
    403: {"description": "Forbidden", "model": ErrorDetail},
}


class IncrementalRequest(BaseModel):
    project_id: uuid.UUID
    asset_ids: list[uuid.UUID] = Field(..., min_length=1)


@router.post(
    "/incremental",
    response_model=DataResponse[JobOut],
    status_code=201,
    summary="Submit incremental ingestion",
    description="Submits new assets for incremental classification against existing knowledge. The system classifies each asset's content as: new (no matching topic), supplement (adds detail), correction (updates outdated knowledge), or conflict (contradicts existing knowledge).",
    responses={
        201: {"description": "Ingestion job created and queued"},
        **_RESP_AUTH,
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def incremental_ingestion(
    body: IncrementalRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """Submit new assets for incremental classification against existing knowledge."""
    svc = JobService(db, tenant_id, current_user.id)
    job = await svc.create(
        project_id=body.project_id,
        job_type="incremental",
        asset_ids=[str(aid) for aid in body.asset_ids],
    )
    return DataResponse(data=JobOut.model_validate(job))
