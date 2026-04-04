"""Tenant model."""

from sqlalchemy import BigInteger, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Tenant(Base):
    __tablename__ = "tenant"
    __table_args__ = (
        Index("ix_tenant_status", "status"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Tenant tiering (v0.51.3)
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="free")  # free/pro/enterprise
    feature_flags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    quota_storage_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    quota_projects: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quota_users: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    users = relationship("User", back_populates="tenant", lazy="selectin")
    projects = relationship("Project", back_populates="tenant", lazy="selectin")
