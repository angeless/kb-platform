"""Ingestion router: incremental ingestion endpoint."""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse
from shared_schemas.job import JobOut

from app.deps import get_current_user, get_db, get_tenant_id
from app.services.job_service import JobService
from shared_models import User

router = APIRouter(prefix="/v1/ingestion", tags=["ingestion"])


class IncrementalRequest(BaseModel):
    project_id: uuid.UUID
    asset_ids: list[uuid.UUID] = Field(..., min_length=1)


@router.post("/incremental", response_model=DataResponse[JobOut], status_code=201)
async def incremental_ingestion(
    body: IncrementalRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    """Submit new assets for incremental classification against existing knowledge.

    The system will classify each new asset's content as:
    - new: no matching topic exists
    - supplement: adds detail to existing topic
    - correction: updates outdated knowledge
    - conflict: contradicts existing knowledge
    """
    svc = JobService(db, tenant_id, current_user.id)
    job = await svc.create(
        project_id=body.project_id,
        job_type="incremental",
        asset_ids=[str(aid) for aid in body.asset_ids],
    )
    return DataResponse(data=JobOut.model_validate(job))
