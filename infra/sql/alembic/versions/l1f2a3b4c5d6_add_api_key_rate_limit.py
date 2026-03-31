"""Add rate_limit_per_minute to api_key table.

Revision ID: l1f2a3b4c5d6
Revises: k0e1f2a3b4c5
Create Date: 2026-03-29
"""
from alembic import op
import sqlalchemy as sa

revision = "l1f2a3b4c5d6"
down_revision = "k0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "api_key",
        sa.Column("rate_limit_per_minute", sa.Integer, nullable=False, server_default="60"),
    )


def downgrade() -> None:
    op.drop_column("api_key", "rate_limit_per_minute")
