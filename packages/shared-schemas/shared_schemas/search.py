"""Search schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TextSearchRequest(BaseModel):
    project_id: UUID
    query: str = Field(..., min_length=1, max_length=500)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SearchHit(BaseModel):
    """A single search result."""
    doc_id: UUID
    title: str
    doc_type: str
    status: str
    node_id: UUID | None
    snippet: str = Field(description="Matched text snippet")
    matched_field: str = Field(description="title or content_md")
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SemanticSearchRequest(BaseModel):
    project_id: UUID
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50)


class SemanticHit(BaseModel):
    """A semantic search result with similarity score."""
    doc_id: UUID
    title: str
    doc_type: str
    status: str
    score: float = Field(description="Cosine similarity score (0-1)")


class HybridSearchRequest(BaseModel):
    project_id: UUID
    query: str = Field(..., min_length=2, max_length=500)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)


class HybridSearchHit(BaseModel):
    """A hybrid search result with combined score and match type."""
    doc_id: UUID
    title: str
    doc_type: str
    status: str
    snippet: str
    score: float = Field(description="Normalized score (0-1)")
    match_type: str = Field(description="keyword, semantic, or keyword+semantic")
