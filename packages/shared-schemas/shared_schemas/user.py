"""User management schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserInviteRequest(BaseModel):
    email: EmailStr
    role: str = Field(
        default="viewer",
        pattern="^(tenant_admin|project_admin|editor|reviewer|viewer)$",
    )


class UserUpdate(BaseModel):
    role: str | None = Field(
        None, pattern="^(tenant_admin|project_admin|editor|reviewer|viewer)$"
    )
    status: str | None = Field(None, pattern="^(active|disabled)$")


class UserOut(BaseModel):
    id: UUID
    kb_id: UUID
    email: str
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
