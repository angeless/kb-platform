"""Pydantic schemas for agent output API."""

from datetime import date
from enum import Enum
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


class AgentSourceRef(BaseModel):
    doc_id: UUID
    title: str
    node_path: list[str] = []


class AgentAskResponse(BaseModel):
    answer: str
    sources: list[AgentSourceRef]
    related_questions: list[str]


# --- Usage statistics schemas ---


class UsageGroupBy(str, Enum):
    day = "day"
    endpoint = "endpoint"


class DailyUsage(BaseModel):
    date: date
    requests: int
    errors: int
    avg_latency_ms: int


class EndpointUsage(BaseModel):
    endpoint: str
    requests: int
    errors: int
    avg_latency_ms: int


class AgentUsageResponse(BaseModel):
    api_key_id: UUID
    period: dict[str, str]  # {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
    total_requests: int
    total_errors: int
    daily: list[DailyUsage] | None = None
    by_endpoint: list[EndpointUsage] | None = None
