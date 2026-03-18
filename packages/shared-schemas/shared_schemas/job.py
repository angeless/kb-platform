"""Job schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    project_id: UUID
    job_type: str = Field(
        ..., pattern="^(ingest|classify|architecture_draft|kb_generate|review_publish|incremental)$"
    )
    asset_id: UUID | None = None  # Required for 'ingest' jobs
    asset_ids: list[UUID] | None = None  # Required for 'incremental' jobs


class JobOut(BaseModel):
    id: UUID
    project_id: UUID
    job_type: str
    status: str
    error_message: str | None
    retry_count: int
    celery_task_id: str | None
    created_by: UUID
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
