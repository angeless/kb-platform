"""add HNSW index on doc_embedding.embedding_vec + backfill data

Revision ID: v1w2x3y4z5a6
Revises: u0i1j2k3l4m5
Create Date: 2026-04-03

Note: embedding_vec column already exists (migration b2c3d4e5f6a7).
This migration only backfills data from JSONB and creates the HNSW index.
"""

from alembic import op
import sqlalchemy as sa

revision = "v1w2x3y4z5a6"
down_revision = "u0i1j2k3l4m5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Backfill embedding_vec from JSONB embedding column
    op.execute("""
        UPDATE doc_embedding
        SET embedding_vec = embedding::vector
        WHERE embedding IS NOT NULL
          AND embedding_vec IS NULL
    """)

    # Step 2: Create HNSW index for cosine similarity search
    # Using CONCURRENTLY to avoid locking the table during index build
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_doc_embedding_vec_hnsw
        ON doc_embedding
        USING hnsw (embedding_vec vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_doc_embedding_vec_hnsw")
    # Note: we don't null out embedding_vec during downgrade — data is preserved
