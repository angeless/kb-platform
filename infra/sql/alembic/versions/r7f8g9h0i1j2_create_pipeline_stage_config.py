"""create pipeline_stage_config table

Revision ID: r7f8g9h0i1j2
Revises: q6e7f8g9h0i1
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "r7f8g9h0i1j2"
down_revision = "q6e7f8g9h0i1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_stage_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage_name", sa.String(50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project_id", "stage_name", name="uq_pipeline_config_project_stage"),
    )
    op.create_index("ix_pipeline_stage_config_project_id", "pipeline_stage_config", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_stage_config_project_id")
    op.drop_table("pipeline_stage_config")
