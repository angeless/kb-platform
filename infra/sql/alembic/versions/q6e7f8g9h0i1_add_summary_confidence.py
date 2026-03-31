"""Add summary_confidence field to knowledge_doc table.

Revision ID: q6e7f8g9h0i1
Revises: p5d6e7f8g9h0
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa

revision = "q6e7f8g9h0i1"
down_revision = "p5d6e7f8g9h0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("knowledge_doc", sa.Column("summary_confidence", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("knowledge_doc", "summary_confidence")
