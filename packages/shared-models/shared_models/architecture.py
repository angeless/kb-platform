"""Architecture and ArchitectureNode models."""

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Architecture(Base):
    __tablename__ = "architecture"
    __table_args__ = (
        Index("ix_architecture_project_status", "project_id", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="0.1.0")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    levels_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    nodes = relationship("ArchitectureNode", back_populates="architecture", lazy="selectin")


class ArchitectureNode(Base):
    __tablename__ = "architecture_node"
    __table_args__ = (
        Index("ix_arch_node_arch_level", "architecture_id", "level"),
        Index("ix_arch_node_parent", "parent_id"),
    )

    architecture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_node.id"), nullable=True
    )
    node_name: Mapped[str] = mapped_column(String(200), nullable=False)
    node_type: Mapped[str] = mapped_column(String(30), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    accept_types: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reject_types: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    update_policy: Mapped[str | None] = mapped_column(String(30), nullable=True)
    review_policy: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    # Relationships
    architecture = relationship("Architecture", back_populates="nodes")
    children = relationship("ArchitectureNode", back_populates="parent", lazy="selectin")
    parent = relationship("ArchitectureNode", back_populates="children", remote_side="ArchitectureNode.id")
