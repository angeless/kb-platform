"""create pipeline_stage_log table

Revision ID: t9h0i1j2k3l4
Revises: s8g9h0i1j2k3
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "t9h0i1j2k3l4"
down_revision = "s8g9h0i1j2k3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_stage_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("job.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage_name", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'running'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_usage", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_stage_log_job_id", "pipeline_stage_log", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_stage_log_job_id")
    op.drop_table("pipeline_stage_log")
