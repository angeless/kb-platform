"""add bridge tables (BridgeSyncRecord, BridgeMapping, BridgeOperation) — v0.53

Revision ID: a6b7c8d9e0f1
Revises: z5a6b7c8d9e0
Create Date: 2026-04-19

This migration introduces three new tables for the bridge service that
synchronizes Hogwarts-KB markdown files with KBSQL. None of the existing
v0.52 tables are touched.

Rollback (downgrade) drops the three tables. Safe — bridge state can be
fully rebuilt by running `python -m bridge sync-once`.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a6b7c8d9e0f1"
down_revision = "z5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # bridge_sync_record: per-file sync state
    op.create_table(
        "bridge_sync_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("kb_root", sa.String(500), nullable=False),
        sa.Column("relative_path", sa.String(1000), nullable=False),
        sa.Column("kb_layer", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("source_format", sa.String(20), nullable=True),
        sa.Column("sync_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("last_kb_mtime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sql_write", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.UniqueConstraint("kb_root", "relative_path", name="uq_bridge_sync_kb_path"),
    )
    op.create_index(
        "ix_bridge_sync_layer_status",
        "bridge_sync_record",
        ["kb_layer", "sync_status"],
    )

    # bridge_mapping: KB path ↔ KBSQL doc/asset mapping
    op.create_table(
        "bridge_mapping",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("kb_root", sa.String(500), nullable=False),
        sa.Column("relative_path", sa.String(1000), nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asset.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("doc_ids", postgresql.JSONB, nullable=True),
        sa.UniqueConstraint("kb_root", "relative_path", name="uq_bridge_mapping_kb_path"),
    )
    op.create_index("ix_bridge_mapping_asset", "bridge_mapping", ["asset_id"])
    op.create_index("ix_bridge_mapping_project", "bridge_mapping", ["project_id"])

    # bridge_operation: append-only audit log
    op.create_table(
        "bridge_operation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("operation_kind", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("kb_root", sa.String(500), nullable=True),
        sa.Column("relative_path", sa.String(1000), nullable=True),
        sa.Column("detail", postgresql.JSONB, nullable=True),
        sa.Column("duration_ms", sa.BigInteger, nullable=True),
    )
    op.create_index("ix_bridge_op_created", "bridge_operation", ["created_at"])
    op.create_index(
        "ix_bridge_op_kind_status",
        "bridge_operation",
        ["operation_kind", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_bridge_op_kind_status", table_name="bridge_operation")
    op.drop_index("ix_bridge_op_created", table_name="bridge_operation")
    op.drop_table("bridge_operation")

    op.drop_index("ix_bridge_mapping_project", table_name="bridge_mapping")
    op.drop_index("ix_bridge_mapping_asset", table_name="bridge_mapping")
    op.drop_table("bridge_mapping")

    op.drop_index("ix_bridge_sync_layer_status", table_name="bridge_sync_record")
    op.drop_table("bridge_sync_record")
