"""Create api_usage_log table.

Revision ID: m2a3b4c5d6e7
Revises: l1f2a3b4c5d6
Create Date: 2026-03-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "m2a3b4c5d6e7"
down_revision = "l1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_usage_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("api_key_id", UUID(as_uuid=True), sa.ForeignKey("api_key.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.String(200), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("status_code", sa.Integer, nullable=False),
        sa.Column("latency_ms", sa.Integer, nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_api_usage_log_key_requested", "api_usage_log", ["api_key_id", "requested_at"])


def downgrade() -> None:
    op.drop_table("api_usage_log")
