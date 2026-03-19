"""Document embedding model for semantic search."""

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover — pgvector optional at import time
    Vector = None  # type: ignore[assignment,misc]

from .base import Base


class DocEmbedding(Base):
    __tablename__ = "doc_embedding"
    __table_args__ = (
        Index("ix_doc_embedding_project", "project_id"),
    )

    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_doc.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project.id"), nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list] = mapped_column(JSONB, nullable=False)
    # pgvector native column — coexists with JSONB during migration period
    embedding_vec = mapped_column(Vector(1536), nullable=True) if Vector else None
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
