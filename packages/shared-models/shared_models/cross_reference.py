"""Cross-reference model: links between knowledge documents across projects."""

import uuid

from sqlalchemy import Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CrossReference(Base):
    __tablename__ = "cross_reference"
    __table_args__ = (
        UniqueConstraint("source_doc_id", "target_doc_id", "relation_type", name="uq_cross_ref_pair"),
        Index("ix_cross_ref_source", "source_doc_id"),
        Index("ix_cross_ref_target", "target_doc_id"),
        Index("ix_cross_ref_tenant", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False
    )
    source_doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_doc.id", ondelete="CASCADE"), nullable=False
    )
    target_doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_doc.id", ondelete="CASCADE"), nullable=False
    )
    relation_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # related, depends_on, extends, contradicts, supersedes
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_by: Mapped[str] = mapped_column(String(20), nullable=False, default="system")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
