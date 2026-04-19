"""Tests for the v0.54 bridge_ingest stage.

Uses an in-memory SQLite DB so the test doesn't need Aiven Postgres
credentials. The bridge_ingest stage is DB-agnostic (uses SQLAlchemy
ORM only) so SQLite works for everything except JSONB-specific queries
(which we don't exercise here).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from shared_models import Base, BridgeOperation, BridgeSyncRecord
from worker.stages.bridge_ingest import bridge_ingest


@pytest.fixture()
def db():
    """In-memory SQLite session with bridge tables created.

    Workaround for SQLite vs PostgreSQL JSONB: register a SQLite type
    compiler that renders JSONB as TEXT (sufficient for these tests —
    we only do round-trip JSON via SQLAlchemy's JSON adapter, no JSONB
    operators).
    """
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.ext.compiler import compiles

    @compiles(JSONB, "sqlite")
    def _jsonb_as_text_for_sqlite(element, compiler, **kw):
        return "TEXT"

    engine = create_engine("sqlite:///:memory:", future=True)

    # Create only the two bridge tables we need (BridgeMapping has FKs to
    # project + asset, which would require creating those tables too).
    BridgeSyncRecord.__table__.create(engine)
    BridgeOperation.__table__.create(engine)

    SessionLocal = sessionmaker(bind=engine, future=True)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
        engine.dispose()


def _ir(rel: str, *, content_hash: str = "deadbeef" * 8, layer: str = "wiki",
        fmt: str = "md", size: int = 1234, fm: dict | None = None,
        body: str = "") -> dict:
    return {
        "relative_path": rel,
        "content_hash": content_hash,
        "kb_layer": layer,
        "source_format": fmt,
        "raw_size": size,
        "frontmatter": fm or {},
        "content_md": body,
    }


def test_bridge_ingest_creates_record(db: Session, tmp_path: Path):
    res = bridge_ingest(
        db,
        ir=_ir("wiki/concepts/foo.md"),
        kb_root=str(tmp_path),
        enable_graph=False,
        enable_visual=False,
    )
    assert res["status"] == "created"
    assert res["graph_triples_upserted"] == 0
    assert res["visual_augmented"] is False
    assert res["sync_record_id"]

    row = db.query(BridgeSyncRecord).one()
    assert row.relative_path == "wiki/concepts/foo.md"
    assert row.kb_layer == "wiki"
    assert row.sync_status == "parsed"

    op = db.query(BridgeOperation).one()
    assert op.operation_kind == "bridge_ingest"
    assert op.detail["outcome"] == "created"


def test_bridge_ingest_unchanged_for_same_hash(db: Session, tmp_path: Path):
    ir = _ir("wiki/concepts/foo.md", content_hash="aaaa" * 16)
    bridge_ingest(db, ir=ir, kb_root=str(tmp_path),
                  enable_graph=False, enable_visual=False)
    res = bridge_ingest(db, ir=ir, kb_root=str(tmp_path),
                        enable_graph=False, enable_visual=False)
    assert res["status"] == "unchanged"
    # Only one BridgeSyncRecord row
    assert db.query(BridgeSyncRecord).count() == 1
    # Two operation log rows
    assert db.query(BridgeOperation).count() == 2


def test_bridge_ingest_updates_for_different_hash(db: Session, tmp_path: Path):
    bridge_ingest(
        db,
        ir=_ir("wiki/concepts/foo.md", content_hash="aaaa" * 16),
        kb_root=str(tmp_path),
        enable_graph=False,
        enable_visual=False,
    )
    res = bridge_ingest(
        db,
        ir=_ir("wiki/concepts/foo.md", content_hash="bbbb" * 16),
        kb_root=str(tmp_path),
        enable_graph=False,
        enable_visual=False,
    )
    assert res["status"] == "updated"
    row = db.query(BridgeSyncRecord).one()
    assert row.content_hash == "bbbb" * 16


def test_bridge_ingest_with_graph(db: Session, tmp_path: Path, monkeypatch):
    """When BRIDGE_GRAPH_ENABLED, triples are upserted to Kuzu."""
    graph_db = tmp_path / "test.graph.kuzu"
    monkeypatch.setenv("BRIDGE_GRAPH_DB_PATH", str(graph_db))
    res = bridge_ingest(
        db,
        ir=_ir(
            "wiki/concepts/foo.md",
            fm={
                "session_id": "cc:2026-04-19-foo",
                "tags": ["llm", "vercel"],
            },
        ),
        kb_root=str(tmp_path),
        enable_graph=True,
        enable_visual=False,
    )
    # Tags + session_id → 3 triples (2 tagged_with + 1 produced_in)
    assert res["graph_triples_upserted"] >= 2
    # Verify Kuzu file was actually created
    assert graph_db.exists()


def test_bridge_ingest_missing_relative_path_raises(db: Session, tmp_path: Path):
    with pytest.raises(ValueError, match="relative_path"):
        bridge_ingest(
            db,
            ir={"content_hash": "x", "kb_layer": "wiki"},
            kb_root=str(tmp_path),
        )


def test_bridge_ingest_visual_dryrun_does_not_modify_kb(db: Session, tmp_path: Path):
    """Visual augmentation is dry-run only in v0.54 — no file write."""
    body_padding = "Detailed paragraph. " * 50
    body = (
        "# Title\n\n## Overview\n\n" + body_padding +
        "\n\n## Step 1: A\n\n" + body_padding +
        "\n\n## Step 2: B\n\n" + body_padding +
        "\n\n## Step 3: C\n\n" + body_padding
    )
    res = bridge_ingest(
        db,
        ir=_ir(
            "wiki/howtos/test.md",
            fm={"type": "howto"},
            body=body,
        ),
        kb_root=str(tmp_path),
        enable_graph=False,
        enable_visual=True,
    )
    # Augmentation flag set, but no files written (no kb_writer call)
    assert res["visual_augmented"] is True
    # No real files in tmp_path
    assert not list(tmp_path.glob("**/*.md"))
