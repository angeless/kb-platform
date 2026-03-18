"""Knowledge document schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeDocOut(BaseModel):
    id: UUID
    project_id: UUID
    node_id: UUID | None
    doc_type: str
    title: str
    current_version: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SourceRefOut(BaseModel):
    id: UUID
    doc_version_id: UUID
    asset_chunk_id: UUID
    location_hint: str | None

    model_config = {"from_attributes": True}


class DocVersionOut(BaseModel):
    id: UUID
    doc_id: UUID
    version: int
    content_md: str
    change_reason: str | None
    created_by: UUID
    created_at: datetime
    source_refs: list[SourceRefOut] = []

    model_config = {"from_attributes": True}


class KnowledgeDocDetailOut(BaseModel):
    """Full document detail including versions and source refs."""
    id: UUID
    project_id: UUID
    node_id: UUID | None
    doc_type: str
    title: str
    current_version: int
    status: str
    created_at: datetime
    updated_at: datetime
    versions: list[DocVersionOut] = []

    model_config = {"from_attributes": True}


class ConflictOut(BaseModel):
    id: UUID
    project_id: UUID
    node_id: UUID | None
    description: str
    status: str
    resolved_by: UUID | None
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConflictResolveRequest(BaseModel):
    resolution_note: str = Field(..., min_length=1)
