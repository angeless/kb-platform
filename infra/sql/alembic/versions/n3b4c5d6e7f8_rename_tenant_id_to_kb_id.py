"""Rename tenant_id to kb_id in all applicable tables.

Revision ID: n3b4c5d6e7f8
Revises: m2a3b4c5d6e7
Create Date: 2026-03-29
"""
from alembic import op

revision = "n3b4c5d6e7f8"
down_revision = "m2a3b4c5d6e7"
branch_labels = None
depends_on = None

# Tables that have a tenant_id column to rename
_TABLES = [
    "user",
    "project",
    "api_key",
    "audit_log",
    "cross_reference",
    "model_provider",
    "model_route",
]


def upgrade() -> None:
    for table in _TABLES:
        op.alter_column(table, "tenant_id", new_column_name="kb_id")


def downgrade() -> None:
    for table in _TABLES:
        op.alter_column(table, "kb_id", new_column_name="tenant_id")
