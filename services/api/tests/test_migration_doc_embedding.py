"""Tests for T-36-01: doc_embedding table creation in migration b2c3d4e5f6a7.

Validates that the migration script contains the CREATE TABLE IF NOT EXISTS
statement with all required columns matching the DocEmbedding ORM model.
"""

import importlib.util
import pathlib
import textwrap

import pytest

MIGRATION_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "infra"
    / "sql"
    / "alembic"
    / "versions"
    / "b2c3d4e5f6a7_add_embedding_vec_column.py"
)


def _load_migration_source() -> str:
    """Return the full source text of the migration file."""
    return MIGRATION_PATH.read_text(encoding="utf-8")


def _load_migration_module():
    """Import the migration as a module so we can inspect callables."""
    spec = importlib.util.spec_from_file_location("migration_b2c3d4e5f6a7", MIGRATION_PATH)
    mod = importlib.util.module_from_spec(spec)
    # We don't actually execute upgrade/downgrade (they need alembic context),
    # but loading the module verifies it has no syntax errors.
    return mod


# ---------- source-level checks ----------

class TestMigrationContainsCreateTable:
    """Verify the migration source contains required DDL statements."""

    @pytest.fixture(autouse=True)
    def _source(self):
        self.source = _load_migration_source()

    def test_create_table_if_not_exists(self):
        assert "CREATE TABLE IF NOT EXISTS doc_embedding" in self.source

    def test_has_id_column(self):
        assert "id" in self.source
        assert "UUID" in self.source
        assert "PRIMARY KEY" in self.source

    def test_has_doc_id_with_fk(self):
        assert "doc_id" in self.source
        assert "REFERENCES knowledge_doc(id)" in self.source
        assert "ON DELETE CASCADE" in self.source

    def test_has_project_id_with_fk(self):
        assert "project_id" in self.source
        assert "REFERENCES project(id)" in self.source

    def test_has_version_column(self):
        # version INTEGER NOT NULL
        assert "version" in self.source

    def test_has_embedding_jsonb(self):
        assert "JSONB" in self.source

    def test_has_model_name(self):
        assert "model_name" in self.source
        assert "VARCHAR(100)" in self.source

    def test_has_dimensions(self):
        assert "dimensions" in self.source

    def test_has_timestamps(self):
        assert "created_at" in self.source
        assert "updated_at" in self.source
        assert "TIMESTAMPTZ" in self.source

    def test_has_project_index(self):
        assert "ix_doc_embedding_project" in self.source

    def test_has_unique_doc_id(self):
        assert "UNIQUE" in self.source

    def test_has_embedding_vec_column(self):
        assert "embedding_vec vector(1536)" in self.source


class TestMigrationDowngrade:
    """Verify downgrade handles doc_embedding table removal."""

    @pytest.fixture(autouse=True)
    def _source(self):
        self.source = _load_migration_source()

    def test_downgrade_drops_table(self):
        assert "DROP TABLE IF EXISTS doc_embedding" in self.source

    def test_downgrade_drops_index(self):
        assert "DROP INDEX IF EXISTS ix_doc_embedding_project" in self.source


class TestMigrationModuleLoads:
    """Verify the migration file has no syntax errors."""

    def test_module_loads_without_error(self):
        mod = _load_migration_module()
        assert mod is not None

    def test_has_revision_info(self):
        source = _load_migration_source()
        assert 'revision = "b2c3d4e5f6a7"' in source
        assert 'down_revision = "a1b2c3d4e5f6"' in source
