"""Batch import models for ZIP bulk upload tracking."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class BatchImport(Base):
    __tablename__ = "batch_import"
    __table_args__ = (
        Index("ix_batch_import_project", "project_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project.id"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    zip_path: Mapped[str] = mapped_column(String(500), nullable=False)
    total_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    assets: Mapped[list["BatchImportAsset"]] = relationship(
        back_populates="batch", lazy="selectin"
    )


class BatchImportAsset(Base):
    __tablename__ = "batch_import_asset"
    __table_args__ = (
        UniqueConstraint("batch_id", "asset_id", name="uq_batch_asset"),
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("batch_import.id"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset.id"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)

    batch: Mapped["BatchImport"] = relationship(back_populates="assets")
