"""add update_type to knowledge_doc

Revision ID: s8g9h0i1j2k3
Revises: r7f8g9h0i1j2
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa

revision = "s8g9h0i1j2k3"
down_revision = "r7f8g9h0i1j2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_doc",
        sa.Column("update_type", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("knowledge_doc", "update_type")
