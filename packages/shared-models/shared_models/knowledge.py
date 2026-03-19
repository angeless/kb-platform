"""Knowledge document models: KnowledgeDoc, KnowledgeDocVersion, SourceRef, ConflictRecord."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UserDefinedType

from .base import Base


class TSVector(UserDefinedType):
    """Custom type for PostgreSQL tsvector."""
    cache_ok = True

    def get_col_spec(self) -> str:
        return "tsvector"


class KnowledgeDoc(Base):
    __tablename__ = "knowledge_doc"
    __table_args__ = (
        Index("ix_knowledge_doc_project_status", "project_id", "status"),
        Index("ix_knowledge_doc_node", "node_id"),
        Index("ix_knowledge_doc_search_vector", "search_vector", postgresql_using="gin"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project.id"), nullable=False
    )
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_node.id"), nullable=True
    )
    doc_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    search_vector = mapped_column(TSVector(), nullable=True)

    # Relationships
    versions = relationship("KnowledgeDocVersion", back_populates="doc", lazy="selectin")


class KnowledgeDocVersion(Base):
    __tablename__ = "knowledge_doc_version"
    __table_args__ = (
        Index("ix_doc_version_doc_version", "doc_id", "version"),
        Index("ix_knowledge_doc_version_search_vector", "search_vector", postgresql_using="gin"),
    )

    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_doc.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    search_vector = mapped_column(TSVector(), nullable=True)

    # Relationships
    doc = relationship("KnowledgeDoc", back_populates="versions")
    source_refs = relationship("SourceRef", back_populates="doc_version", lazy="selectin")


class SourceRef(Base):
    __tablename__ = "source_ref"

    doc_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_doc_version.id", ondelete="CASCADE"), nullable=False
    )
    asset_chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_chunk.id"), nullable=False
    )
    location_hint: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Relationships
    doc_version = relationship("KnowledgeDocVersion", back_populates="source_refs")


class ConflictRecord(Base):
    __tablename__ = "conflict_record"
    __table_args__ = (
        Index("ix_conflict_project_status", "project_id", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project.id"), nullable=False
    )
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_node.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
