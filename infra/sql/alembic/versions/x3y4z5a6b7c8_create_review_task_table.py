"""create review_task table

Revision ID: x3y4z5a6b7c8
Revises: w2x3y4z5a6b7
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "x3y4z5a6b7c8"
down_revision = "w2x3y4z5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_task",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project.id"), nullable=False),
        sa.Column("doc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_doc.id"), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_review_task_project", "review_task", ["project_id"])
    op.create_index("ix_review_task_doc", "review_task", ["doc_id"])
    op.create_index("ix_review_task_reviewer", "review_task", ["reviewer_id"])


def downgrade() -> None:
    op.drop_index("ix_review_task_reviewer")
    op.drop_index("ix_review_task_doc")
    op.drop_index("ix_review_task_project")
    op.drop_table("review_task")
