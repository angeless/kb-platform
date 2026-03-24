"""Add cross_reference table and project profile fields.

Revision ID: h7b8c9d0e1f2
Revises: g6a7b8c9d0e1
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "h7b8c9d0e1f2"
down_revision = "g6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Cross-reference table
    op.create_table(
        "cross_reference",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("source_doc_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_doc.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_doc_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_doc.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("created_by", sa.String(20), nullable=False, server_default="system"),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("source_doc_id", "target_doc_id", "relation_type", name="uq_cross_ref_pair"),
    )
    op.create_index("ix_cross_ref_source", "cross_reference", ["source_doc_id"])
    op.create_index("ix_cross_ref_target", "cross_reference", ["target_doc_id"])
    op.create_index("ix_cross_ref_tenant", "cross_reference", ["tenant_id"])

    # Project profile fields for multi-library routing
    op.add_column("project", sa.Column("profile_keywords", JSONB, nullable=True))
    op.add_column("project", sa.Column("profile_embedding", JSONB, nullable=True))
    op.add_column("project", sa.Column("description", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("project", "description")
    op.drop_column("project", "profile_embedding")
    op.drop_column("project", "profile_keywords")
    op.drop_index("ix_cross_ref_tenant")
    op.drop_index("ix_cross_ref_target")
    op.drop_index("ix_cross_ref_source")
    op.drop_table("cross_reference")
