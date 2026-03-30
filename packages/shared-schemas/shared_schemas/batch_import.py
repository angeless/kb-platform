"""Batch import request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BatchImportFileOut(BaseModel):
    asset_id: UUID
    original_filename: str
    parse_status: str

    model_config = {"from_attributes": True}


class BatchImportOut(BaseModel):
    batch_id: UUID
    status: str
    total_files: int
    completed_files: int
    failed_files: int
    created_at: datetime
    files: list[BatchImportFileOut]


class BatchImportCreatedOut(BaseModel):
    batch_id: UUID
    total_files: int
    skipped_files: int
