"""Bridge service models (v0.53+).

Three tables track the KBSQL ↔ Hogwarts-KB sync:

- BridgeSyncRecord: per-file sync state (path, hash, last write timestamps).
  One row per KB file the bridge has seen. Used by kb_watcher to skip
  unchanged files.

- BridgeMapping: explicit KB-path ↔ KBSQL doc/asset_id mapping. Lets us look
  up "what's the doc_id for wiki/concepts/foo.md?" without a join.

- BridgeOperation: append-only audit log of bridge actions. Diagnoses sync
  issues without grepping logs.

These models intentionally do NOT have FK to Project. The bridge can run in
project-less mode for personal-KB use cases (the v0.53 default). Project
binding is added later via BridgeMapping.project_id (nullable).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BridgeSyncRecord(Base):
    """Per-file sync state for the KB ↔ KBSQL bridge.

    One row per KB file path that the bridge has touched. The (kb_root,
    relative_path) pair is the natural key — multiple KBs can sync into the
    same KBSQL instance by varying kb_root.
    """

    __tablename__ = "bridge_sync_record"
    __table_args__ = (
        UniqueConstraint("kb_root", "relative_path", name="uq_bridge_sync_kb_path"),
        Index("ix_bridge_sync_layer_status", "kb_layer", "sync_status"),
    )

    kb_root: Mapped[str] = mapped_column(
        String(500), nullable=False,
        comment="Absolute path to the KB root (HOGWARTS_KB_PATH at sync time)",
    )
    relative_path: Mapped[str] = mapped_column(
        String(1000), nullable=False,
        comment="Path relative to kb_root, e.g. wiki/concepts/foo.md",
    )
    kb_layer: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown",
        comment="One of: raw-sources | wiki | lessons | memory | unknown",
    )
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="sha256 of canonical content_md from parser; None if file deleted",
    )
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_format: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="File extension (md, pdf, docx, ...) at last sync",
    )
    sync_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="pending | parsed | ingested | error | deleted",
    )
    last_kb_mtime: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="The KB file's mtime when last seen by watcher",
    )
    last_sql_write: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When KBSQL last persisted a derived doc for this file",
    )
    last_error: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Most recent parse/ingest error message (truncated to 1000 chars)",
    )


class BridgeMapping(Base):
    """KB path ↔ KBSQL doc_id / asset_id mapping.

    A single KB file may produce one Asset (raw bytes / IR) and zero-or-more
    KnowledgeDoc rows (depending on pipeline output). This table records the
    canonical asset_id, plus optional doc_id list as JSONB.
    """

    __tablename__ = "bridge_mapping"
    __table_args__ = (
        UniqueConstraint(
            "kb_root", "relative_path", name="uq_bridge_mapping_kb_path"
        ),
        Index("ix_bridge_mapping_asset", "asset_id"),
        Index("ix_bridge_mapping_project", "project_id"),
    )

    kb_root: Mapped[str] = mapped_column(String(500), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project.id", ondelete="SET NULL"),
        nullable=True,
        comment="Project this KB file is associated with; null = personal KB mode",
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset.id", ondelete="SET NULL"),
        nullable=True,
    )
    doc_ids: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        comment="JSON array of knowledge_doc.id strings produced from this file",
    )


class BridgeOperation(Base):
    """Append-only log of bridge operations for diagnostic / audit.

    Every meaningful bridge action (file detected, parsed, ingested, written
    back, push to git, error) gets one row. Retention policy is informal —
    truncate manually or via a maintenance job; this table is not on the
    hot path of any user-facing query.
    """

    __tablename__ = "bridge_operation"
    __table_args__ = (
        Index("ix_bridge_op_created", "created_at"),
        Index("ix_bridge_op_kind_status", "operation_kind", "status"),
    )

    operation_kind: Mapped[str] = mapped_column(
        String(40), nullable=False,
        comment="watch_detect | parse | ingest | write_back | git_push | sync_full | error",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="ok | warn | error",
    )
    kb_root: Mapped[str | None] = mapped_column(String(500), nullable=True)
    relative_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    detail: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Free-form structured detail (counts, hashes, error stack, etc.)",
    )
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
