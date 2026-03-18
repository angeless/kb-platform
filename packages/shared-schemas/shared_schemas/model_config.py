"""Model provider and route schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ModelProviderCreate(BaseModel):
    provider_name: str = Field(..., min_length=1, max_length=50)
    api_key: str = Field(..., min_length=1)
    base_url: str | None = Field(None, max_length=500)
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    max_context: int = Field(default=4096, ge=1)


class ModelProviderOut(BaseModel):
    id: UUID
    tenant_id: UUID
    provider_name: str
    api_key_masked: str
    base_url: str | None
    timeout_seconds: int
    max_context: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelProviderTestRequest(BaseModel):
    provider_id: UUID


class ModelRouteCreate(BaseModel):
    task_type: str = Field(..., min_length=1, max_length=30)
    provider_id: UUID
    model_name: str = Field(..., min_length=1, max_length=100)
    priority: int = Field(default=0, ge=0)
    cost_limit_usd: Decimal | None = Field(None, ge=0)


class ModelRouteUpdate(BaseModel):
    model_name: str | None = Field(None, min_length=1, max_length=100)
    priority: int | None = Field(None, ge=0)
    cost_limit_usd: Decimal | None = Field(None, ge=0)


class ModelRouteOut(BaseModel):
    id: UUID
    tenant_id: UUID
    task_type: str
    provider_id: UUID
    model_name: str
    priority: int
    cost_limit_usd: Decimal | None
    created_at: datetime

    model_config = {"from_attributes": True}
