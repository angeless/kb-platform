"""Project schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    industry_hint: str | None = Field(None, max_length=100)


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    industry_hint: str | None = Field(None, max_length=100)
    status: str | None = Field(None, pattern="^(active|archived)$")


class ProjectOut(BaseModel):
    id: UUID
    kb_id: UUID
    name: str
    industry_hint: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
