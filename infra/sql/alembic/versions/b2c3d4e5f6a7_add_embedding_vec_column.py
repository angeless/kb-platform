"""Create doc_embedding table (if missing) and add embedding_vec vector(1536) column.

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
    # --- Fix: doc_embedding table was never created in initial_schema migration.
    # CREATE TABLE IF NOT EXISTS ensures idempotency on databases where the
    # table already exists (e.g. created via Base.metadata.create_all).
    op.execute("""
        CREATE TABLE IF NOT EXISTS doc_embedding (
            id              UUID            PRIMARY KEY,
            doc_id          UUID            NOT NULL UNIQUE
                                            REFERENCES knowledge_doc(id) ON DELETE CASCADE,
            project_id      UUID            NOT NULL
                                            REFERENCES project(id),
            version         INTEGER         NOT NULL,
            embedding       JSONB           NOT NULL,
            model_name      VARCHAR(100)    NOT NULL,
            dimensions      INTEGER         NOT NULL,
            created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_doc_embedding_project
        ON doc_embedding (project_id)
    """)

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
    op.execute("DROP INDEX IF EXISTS ix_doc_embedding_project")
    op.execute("DROP TABLE IF EXISTS doc_embedding")
