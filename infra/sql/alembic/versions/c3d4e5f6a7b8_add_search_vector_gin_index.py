"""Add tsvector search_vector columns and GIN indexes.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-19
"""

from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tsvector columns
    op.execute(
        "ALTER TABLE knowledge_doc ADD COLUMN IF NOT EXISTS search_vector tsvector"
    )
    op.execute(
        "ALTER TABLE knowledge_doc_version ADD COLUMN IF NOT EXISTS search_vector tsvector"
    )

    # Create GIN indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_knowledge_doc_search_vector
        ON knowledge_doc USING gin(search_vector)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_knowledge_doc_version_search_vector
        ON knowledge_doc_version USING gin(search_vector)
    """)

    # Back-fill search_vector for existing docs using 'simple' config
    # (works for all languages including CJK at character level)
    op.execute("""
        UPDATE knowledge_doc
        SET search_vector = to_tsvector('simple', coalesce(title, ''))
        WHERE search_vector IS NULL
    """)
    op.execute("""
        UPDATE knowledge_doc_version
        SET search_vector = to_tsvector('simple', coalesce(content_md, ''))
        WHERE search_vector IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_doc_version_search_vector")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_doc_search_vector")
    op.drop_column("knowledge_doc_version", "search_vector")
    op.drop_column("knowledge_doc", "search_vector")
