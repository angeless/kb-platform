"""Add pgvector extension.

Revision ID: a1b2c3d4e5f6
Revises: df611e31f58f
Create Date: 2026-03-19
"""

from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "df611e31f58f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
