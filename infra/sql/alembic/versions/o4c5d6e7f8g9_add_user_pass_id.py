"""Add pass_id to user table and make password_hash nullable.

Revision ID: o4c5d6e7f8g9
Revises: n3b4c5d6e7f8
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa

revision = "o4c5d6e7f8g9"
down_revision = "n3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("pass_id", sa.String(255), nullable=True))
    op.create_index(
        "ix_user_pass_id",
        "user",
        ["pass_id"],
        unique=True,
        postgresql_where=sa.text("pass_id IS NOT NULL"),
    )
    op.alter_column("user", "password_hash", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    op.alter_column("user", "password_hash", existing_type=sa.String(255), nullable=False)
    op.drop_index("ix_user_pass_id", table_name="user")
    op.drop_column("user", "pass_id")
