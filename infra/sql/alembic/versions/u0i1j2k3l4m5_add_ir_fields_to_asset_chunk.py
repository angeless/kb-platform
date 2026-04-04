"""add IR fields to asset_chunk

Revision ID: u0i1j2k3l4m5
Revises: t9h0i1j2k3l4
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "u0i1j2k3l4m5"
down_revision = "t9h0i1j2k3l4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("asset_chunk", sa.Column("original_format", sa.String(20), nullable=True))
    op.add_column("asset_chunk", sa.Column("structure_type", sa.String(20), nullable=True))
    op.add_column("asset_chunk", sa.Column("extraction_confidence", sa.Float(), nullable=True))
    op.add_column("asset_chunk", sa.Column("semantic_boundaries", postgresql.JSONB(), nullable=True))
    op.add_column("asset_chunk", sa.Column("language", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("asset_chunk", "language")
    op.drop_column("asset_chunk", "semantic_boundaries")
    op.drop_column("asset_chunk", "extraction_confidence")
    op.drop_column("asset_chunk", "structure_type")
    op.drop_column("asset_chunk", "original_format")
