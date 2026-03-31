"""Add summary field to knowledge_doc table.

Revision ID: p5d6e7f8g9h0
Revises: o4c5d6e7f8g9
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa

revision = "p5d6e7f8g9h0"
down_revision = "o4c5d6e7f8g9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("knowledge_doc", sa.Column("summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("knowledge_doc", "summary")
