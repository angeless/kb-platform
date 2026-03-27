"""User model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "user"
    __table_args__ = (
        Index("ix_user_tenant_status", "tenant_id", "status"),
        UniqueConstraint("email", "tenant_id", name="uq_user_email_tenant"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)  # M-15: uniqueness per tenant via table constraint
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="viewer")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Password reset fields
    reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
