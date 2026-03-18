"""Architecture schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ArchitectureOut(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    version: str
    status: str
    levels_json: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NodeCreate(BaseModel):
    parent_id: UUID | None = None
    node_name: str = Field(..., min_length=1, max_length=200)
    node_type: str = Field(..., pattern="^(category|topic|document|glossary|conflict|index)$")
    level: int = Field(default=0, ge=0)
    description: str | None = None
    accept_types: dict | None = None
    reject_types: dict | None = None
    update_policy: str | None = None
    review_policy: str | None = None


class NodeUpdate(BaseModel):
    node_name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    accept_types: dict | None = None
    reject_types: dict | None = None
    update_policy: str | None = None
    review_policy: str | None = None
    status: str | None = Field(None, pattern="^(draft|reviewing|published|deprecated)$")


class NodeOut(BaseModel):
    id: UUID
    architecture_id: UUID
    parent_id: UUID | None
    node_name: str
    node_type: str
    level: int
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
