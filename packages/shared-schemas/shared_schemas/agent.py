"""Pydantic schemas for agent output API."""

from uuid import UUID

from pydantic import BaseModel, Field


class AgentSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class SourceAsset(BaseModel):
    asset_id: UUID
    filename: str
    asset_type: str


class AgentSearchHit(BaseModel):
    doc_id: UUID
    title: str
    doc_type: str
    snippet: str
    score: float | None = None
    node_path: list[str]
    source_assets: list[SourceAsset]


class AgentSearchResponse(BaseModel):
    results: list[AgentSearchHit]
    total: int


class AgentAskRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class AgentAskResponse(BaseModel):
    answer: str
    sources: list[dict]
    related_questions: list[str]
