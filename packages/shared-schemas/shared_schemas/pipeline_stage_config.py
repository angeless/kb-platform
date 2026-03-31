"""Pipeline stage config request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


STAGE_NAMES = [
    "classify",
    "architecture_draft",
    "doc_generate",
    "quality_check",
    "conflict_detect",
    "embed",
    "review_notify",
]

DEFAULT_STAGE_PARAMS: dict[str, dict] = {
    "classify": {"confidence_threshold": 0.7},
    "architecture_draft": {},
    "doc_generate": {"max_length": 5000},
    "quality_check": {"min_content_length": 50, "require_title": True},
    "conflict_detect": {"similarity_threshold": 0.85},
    "embed": {"model": "default"},
    "review_notify": {},
}


class PipelineStageConfigUpdate(BaseModel):
    enabled: bool = Field(default=True)
    params: dict = Field(default_factory=dict)


class PipelineStageConfigOut(BaseModel):
    stage_name: str
    enabled: bool
    params: dict

    model_config = {"from_attributes": True}


class PipelineStageConfigDetailOut(BaseModel):
    id: UUID
    project_id: UUID
    stage_name: str
    enabled: bool
    params: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PipelineConfigListOut(BaseModel):
    stages: list[PipelineStageConfigOut]
