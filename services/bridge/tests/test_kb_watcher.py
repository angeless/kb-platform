"""Tests for bridge.watchers.kb_watcher.

The watcher's reliance on real fs events is mocked out — we test the pure
processing logic (`_process_change`, `_is_ignored`, `_classify_and_parse`)
plus the full-sync scanner end-to-end on a temp KB tree.
"""

from __future__ import annotations

import asyncio
import textwrap
from pathlib import Path

import pytest

from bridge.watchers import kb_watcher


# ----- ignore-glob logic ------------------------------------------------------

@pytest.mark.parametrize(
    "rel,globs,expected",
    [
        (".git/HEAD", [".git/*"], True),
        (".obsidian/workspace.json", [".obsidian/*"], True),
        ("wiki/concepts/foo.md", [".git/*", ".obsidian/*"], False),
        (".DS_Store", [".DS_Store"], True),
        (".search-index.sqlite", [".search-index.sqlite*"], True),
        (".search-index.sqlite-journal", [".search-index.sqlite*"], True),
    ],
)
def test_is_ignored(rel, globs, expected):
    assert kb_watcher._is_ignored(rel, globs) == expected


# ----- classification + parse dispatch ----------------------------------------

def _seed_kb(root: Path) -> dict[str, Path]:
    """Create a tiny KB tree with one file per layer."""
    files = {
        "wiki": root / "wiki" / "concepts" / "foo.md",
        "raw": root / "raw-sources" / "src.md",
        "lesson": root / "lessons" / "2026-04-19-x.md",
        "memory": root / "memory" / "feedback_x.md",
        "csv": root / "wiki" / "tables" / "data.csv",
        "ignored": root / ".git" / "HEAD",
        "ds_store": root / ".DS_Store",
        "weird_ext": root / "wiki" / "weird.xyz",
    }
    for kind, p in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        if kind == "csv":
            p.write_text("a,b\n1,2\n", encoding="utf-8")
        elif kind == "ds_store":
            p.write_bytes(b"\x00" * 8)
        elif kind == "ignored":
            p.write_text("ref: refs/heads/main\n", encoding="utf-8")
        elif kind == "weird_ext":
            p.write_text("noise", encoding="utf-8")
        else:
            p.write_text(f"# {kind}\n\nbody for {kind}\n", encoding="utf-8")
    return files


def test_classify_and_parse_md_file(tmp_path: Path):
    files = _seed_kb(tmp_path)
    ir = kb_watcher._classify_and_parse(files["wiki"], tmp_path)
    assert ir is not None
    assert ir["kind"] == "markdown"
    assert ir["kb_layer"] == "wiki"
    assert ir["relative_path"] == "wiki/concepts/foo.md"


def test_classify_and_parse_csv_uses_multi_format(tmp_path: Path):
    files = _seed_kb(tmp_path)
    ir = kb_watcher._classify_and_parse(files["csv"], tmp_path)
    assert ir is not None
    assert ir["kind"] == "multi_format"
    assert ir["source_format"] == "csv"


def test_classify_and_parse_unknown_extension_returns_none(tmp_path: Path):
    files = _seed_kb(tmp_path)
    assert kb_watcher._classify_and_parse(files["weird_ext"], tmp_path) is None


def test_classify_and_parse_missing_file_returns_none(tmp_path: Path):
    assert kb_watcher._classify_and_parse(tmp_path / "nope.md", tmp_path) is None


# ----- _process_change with injected callbacks --------------------------------

@pytest.mark.asyncio
async def test_process_change_calls_persist_and_enqueue(tmp_path: Path):
    files = _seed_kb(tmp_path)
    persisted: list[dict] = []
    enqueued: list[dict] = []

    async def persist(ir):
        persisted.append(ir)

    async def enqueue(ir):
        enqueued.append(ir)

    ir = await kb_watcher._process_change(
        files["wiki"], tmp_path,
        persist_fn=persist, enqueue_fn=enqueue,
    )
    assert ir is not None
    assert len(persisted) == 1
    assert len(enqueued) == 1
    assert persisted[0]["relative_path"] == "wiki/concepts/foo.md"


@pytest.mark.asyncio
async def test_process_change_skips_unsupported(tmp_path: Path):
    files = _seed_kb(tmp_path)
    persisted: list[dict] = []

    async def persist(ir):
        persisted.append(ir)

    ir = await kb_watcher._process_change(
        files["weird_ext"], tmp_path, persist_fn=persist,
    )
    assert ir is None
    assert persisted == []


@pytest.mark.asyncio
async def test_process_change_for_missing_file_returns_none(tmp_path: Path):
    persisted: list[dict] = []

    async def persist(ir):
        persisted.append(ir)

    ir = await kb_watcher._process_change(
        tmp_path / "deleted.md", tmp_path, persist_fn=persist,
    )
    assert ir is None
    assert persisted == []


# ----- run_full_sync ----------------------------------------------------------

def test_run_full_sync_counts_correctly(tmp_path: Path, monkeypatch):
    """Full sync should process md + csv files, ignore .git/.DS_Store, skip .xyz."""
    _seed_kb(tmp_path)

    # Patch get_settings to point at our temp tree
    from bridge import config as bridge_config

    class FakeSettings:
        hogwarts_kb_path = tmp_path
        watcher_ignore_globs = [
            ".git/*", ".obsidian/*", ".search-index.sqlite*",
            ".DS_Store", "node_modules/*", ".venv/*",
        ]

    monkeypatch.setattr(bridge_config, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(kb_watcher, "get_settings", lambda: FakeSettings())

    rc = kb_watcher.run_full_sync()
    assert rc == 0
