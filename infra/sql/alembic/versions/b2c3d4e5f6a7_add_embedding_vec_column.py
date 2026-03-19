"""Add embedding_vec vector(1536) column to doc_embedding.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add vector column
    op.execute(
        "ALTER TABLE doc_embedding ADD COLUMN IF NOT EXISTS embedding_vec vector(1536)"
    )

    # Back-fill from JSONB where data exists and has correct dimensions.
    # The cast embedding::text::vector handles JSONB array → vector conversion.
    # Skip rows with null embedding, wrong dimensions, or invalid values.
    op.execute("""
        UPDATE doc_embedding
        SET embedding_vec = embedding::text::vector(1536)
        WHERE embedding IS NOT NULL
          AND jsonb_array_length(embedding) = 1536
          AND embedding_vec IS NULL
    """)


def downgrade() -> None:
    op.drop_column("doc_embedding", "embedding_vec")
