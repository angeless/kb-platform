"""Audit log schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: UUID
    kb_id: UUID
    project_id: UUID | None
    user_id: UUID
    action: str
    resource_type: str
    resource_id: UUID
    detail: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
