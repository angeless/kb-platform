"""Model provider and model route configuration models."""

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ModelProvider(Base):
    __tablename__ = "model_provider"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False
    )
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    max_context: Mapped[int] = mapped_column(Integer, nullable=False, default=4096)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Relationships
    routes = relationship("ModelRoute", back_populates="provider", lazy="selectin")


class ModelRoute(Base):
    __tablename__ = "model_route"
    __table_args__ = (
        Index("ix_model_route_tenant_task", "tenant_id", "task_type"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False
    )
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_provider.id"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_limit_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Relationships
    provider = relationship("ModelProvider", back_populates="routes")
