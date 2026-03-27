"""M-15: Change email uniqueness from global to per-tenant.

Revision ID: i8c9d0e1f2a3
Revises: h7b8c9d0e1f2
Create Date: 2026-03-24
"""
from alembic import op

revision = "i8c9d0e1f2a3"
down_revision = "h7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop global email unique constraint
    op.drop_constraint("user_email_key", "user", type_="unique")
    # Add tenant-scoped email uniqueness
    op.create_unique_constraint("uq_user_email_tenant", "user", ["email", "tenant_id"])


def downgrade() -> None:
    op.drop_constraint("uq_user_email_tenant", "user", type_="unique")
    op.create_unique_constraint("user_email_key", "user", ["email"])
