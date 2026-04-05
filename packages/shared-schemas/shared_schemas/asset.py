"""Asset schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class AssetOut(BaseModel):
    id: UUID
    project_id: UUID
    asset_type: str
    filename: str
    source_url: str | None
    file_hash: str | None
    file_size: int | None
    parse_status: str
    uploaded_by: UUID
    uploaded_at: datetime
    tags: dict | None = None  # Aggregated from first chunk (v0.52.10 — Gap-15 fix)

    model_config = {"from_attributes": True}


class ImportUrlRequest(BaseModel):
    project_id: UUID
    url: HttpUrl


class ImportArchiveRequest(BaseModel):
    project_id: UUID
