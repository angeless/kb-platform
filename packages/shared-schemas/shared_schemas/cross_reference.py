"""Pydantic schemas for cross-reference API."""

from uuid import UUID

from pydantic import BaseModel, Field


class CrossRefCreate(BaseModel):
    source_doc_id: UUID
    target_doc_id: UUID
    relation_type: str = Field(pattern=r"^(related|depends_on|extends|contradicts|supersedes)$")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    note: str | None = None


class CrossRefOut(BaseModel):
    id: str
    source_doc_id: str
    target_doc_id: str
    relation_type: str
    confidence: float
    created_by: str
    note: str | None
    # Enriched fields (joined from KnowledgeDoc)
    source_title: str | None = None
    target_title: str | None = None
    target_project_id: str | None = None
    target_project_name: str | None = None

    model_config = {"from_attributes": True}


class AutoSuggestRequest(BaseModel):
    doc_id: UUID
    max_results: int = Field(default=5, ge=1, le=20)


class RouteContentRequest(BaseModel):
    embedding: list[float] | None = None
    keywords: list[str] | None = None
    exclude_project_id: UUID | None = None


class RoutingResult(BaseModel):
    project_id: str
    project_name: str
    confidence: float
    reason: str
