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
    # Step 1: Backfill embedding_vec from JSONB embedding column.
    # Cast via ::text first because pgvector has no direct jsonb→vector cast
    # (fix 2026-04-19 — migration was failing on Postgres 17 + pgvector 0.8).
    op.execute("""
        UPDATE doc_embedding
        SET embedding_vec = embedding::text::vector
        WHERE embedding IS NOT NULL
          AND embedding_vec IS NULL
    """)

    # Step 2: Create HNSW index for cosine similarity search.
    # Note: CONCURRENTLY removed (2026-04-19) because alembic wraps each
    # migration in a transaction, and CREATE INDEX CONCURRENTLY cannot run
    # inside one. For initial setup on empty/small tables this is fine.
    # If you need CONCURRENTLY for a hot prod table, run that statement
    # manually outside alembic.
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_doc_embedding_vec_hnsw
        ON doc_embedding
        USING hnsw (embedding_vec vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_doc_embedding_vec_hnsw")
    # Note: we don't null out embedding_vec during downgrade — data is preserved
