"""add tenant tier fields + user org fields

Revision ID: y4z5a6b7c8d9
Revises: x3y4z5a6b7c8
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "y4z5a6b7c8d9"
down_revision = "x3y4z5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # v0.51.3: Tenant tiering
    op.add_column("tenant", sa.Column("tier", sa.String(20), nullable=False, server_default="free"))
    op.add_column("tenant", sa.Column("feature_flags", postgresql.JSONB(), nullable=True))
    op.add_column("tenant", sa.Column("quota_storage_bytes", sa.BigInteger(), nullable=True))
    op.add_column("tenant", sa.Column("quota_projects", sa.Integer(), nullable=True))
    op.add_column("tenant", sa.Column("quota_users", sa.Integer(), nullable=True))

    # v0.51.4: User org hierarchy
    op.add_column("user", sa.Column("department", sa.String(100), nullable=True))
    op.add_column("user", sa.Column("team", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "team")
    op.drop_column("user", "department")
    op.drop_column("tenant", "quota_users")
    op.drop_column("tenant", "quota_projects")
    op.drop_column("tenant", "quota_storage_bytes")
    op.drop_column("tenant", "feature_flags")
    op.drop_column("tenant", "tier")
