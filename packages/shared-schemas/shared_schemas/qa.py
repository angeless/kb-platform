"""QA (Question & Answer) request/response schemas."""

import uuid

from pydantic import BaseModel, Field


class QARequest(BaseModel):
    project_id: uuid.UUID
    question: str = Field(..., min_length=5, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class QASource(BaseModel):
    doc_id: uuid.UUID
    title: str
    snippet: str
    relevance: float


class QAResponse(BaseModel):
    answer: str
    sources: list[QASource]
    related_questions: list[str]
