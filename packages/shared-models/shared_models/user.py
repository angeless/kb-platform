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
        Index("ix_user_tenant_status", "kb_id", "status"),
        Index("ix_user_pass_id", "pass_id", unique=True, postgresql_where="pass_id IS NOT NULL"),
        UniqueConstraint("email", "kb_id", name="uq_user_email_tenant"),
    )

    kb_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False
    )
    pass_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)  # M-15: uniqueness per tenant via table constraint
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="viewer")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Organization hierarchy (v0.51.4)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    team: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Password reset fields
    reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
