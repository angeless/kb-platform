"""Add keywords and knowledge_type to knowledge_doc.

Revision ID: g6a7b8c9d0e1
Revises: f5a6b7c8d9e0
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "g6a7b8c9d0e1"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("knowledge_doc", sa.Column("keywords", JSONB, nullable=True))
    op.add_column("knowledge_doc", sa.Column("knowledge_type", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("knowledge_doc", "knowledge_type")
    op.drop_column("knowledge_doc", "keywords")
