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


class DocVersionSummaryOut(BaseModel):
    """Version list item — no content_md to reduce payload."""
    version: int
    change_reason: str | None
    created_by: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class DocVersionListOut(BaseModel):
    """Response for GET /v1/docs/{doc_id}/versions."""
    versions: list[DocVersionSummaryOut]
    total: int
    current_version: int


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


class DiffLineOut(BaseModel):
    """A single line in a version diff."""
    type: str = Field(description="context, added, or removed")
    content: str


class DiffStatsOut(BaseModel):
    added: int
    removed: int
    unchanged: int


class VersionDiffOut(BaseModel):
    """Diff between two versions of a document."""
    doc_id: UUID
    from_version: int
    to_version: int
    from_change_reason: str | None
    to_change_reason: str | None
    diff_lines: list[DiffLineOut]
    stats: DiffStatsOut


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


class AssignNodeRequest(BaseModel):
    node_id: UUID


class DocUpdateContent(BaseModel):
    content_md: str = Field(..., min_length=1)
    change_reason: str = Field(..., min_length=1)


class DocRejectRequest(BaseModel):
    reject_reason: str = Field(..., min_length=1)


class BatchDocRequest(BaseModel):
    doc_ids: list[UUID] = Field(..., min_length=1, max_length=50)


class BatchFailedItem(BaseModel):
    id: UUID
    error_code: str
    message: str


class BatchResultOut(BaseModel):
    succeeded: list[UUID]
    failed: list[BatchFailedItem]
