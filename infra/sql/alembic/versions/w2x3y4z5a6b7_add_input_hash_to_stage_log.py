"""add input_hash to pipeline_stage_log

Revision ID: w2x3y4z5a6b7
Revises: v1w2x3y4z5a6
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa

revision = "w2x3y4z5a6b7"
down_revision = "v1w2x3y4z5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pipeline_stage_log", sa.Column("input_hash", sa.String(64), nullable=True))
    op.create_index("ix_stage_log_idempotent", "pipeline_stage_log", ["job_id", "stage_name", "input_hash"])


def downgrade() -> None:
    op.drop_index("ix_stage_log_idempotent")
    op.drop_column("pipeline_stage_log", "input_hash")
