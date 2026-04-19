"""Tests for bridge_graph.store + bridge_graph.extract."""

from __future__ import annotations

from pathlib import Path

import pytest

from bridge_graph import (
    ExtractionMode,
    GraphStore,
    GraphStoreError,
    Triple,
    extract_triples,
)


# ----- store ------------------------------------------------------------------

def test_store_ping_after_init(tmp_path: Path):
    gs = GraphStore(tmp_path / "x.kuzu")
    assert gs.ping() is True


def test_store_creates_db_parent_dir(tmp_path: Path):
    nested = tmp_path / "nested" / "deeper" / "x.kuzu"
    gs = GraphStore(nested)
    assert nested.parent.exists()
    assert gs.ping()


def test_upsert_page_idempotent(tmp_path: Path):
    gs = GraphStore(tmp_path / "x.kuzu")
    gs.upsert_page("wiki/concepts/foo", layer="wiki", kind="concept")
    # Second upsert with different layer should update, not duplicate
    gs.upsert_page("wiki/concepts/foo", layer="wiki", kind="concept")
    s = gs.stats()
    assert s["pages"] == 1


def test_upsert_episode_with_pchain(tmp_path: Path):
    gs = GraphStore(tmp_path / "x.kuzu")
    gs.upsert_episode(
        "cc:2026-04-19-child",
        parent_session_id="cc:2026-04-18-parent",
        source="claude-code",
    )
    chain = gs.get_p_chain("cc:2026-04-19-child")
    # chain includes self + ancestor (Kuzu *0..N variable-length includes 0-hop)
    assert "cc:2026-04-19-child" in chain
    assert "cc:2026-04-18-parent" in chain


def test_upsert_triples_creates_references(tmp_path: Path):
    gs = GraphStore(tmp_path / "x.kuzu")
    triples = [
        Triple("wiki/concepts/foo", "references_", "wiki/concepts/bar",
               {"kind": "wiki-link"}),
        Triple("wiki/concepts/foo", "references_", "wiki/concepts/baz",
               {"kind": "wiki-link"}),
    ]
    n = gs.upsert_triples(triples)
    assert n == 2

    s = gs.stats()
    assert s["pages"] == 3  # foo, bar, baz auto-created
    assert s["references_"] == 2


def test_get_neighbors(tmp_path: Path):
    gs = GraphStore(tmp_path / "x.kuzu")
    gs.upsert_triples([
        Triple("a", "references_", "b"),
        Triple("b", "references_", "c"),
        Triple("a", "references_", "d"),
    ])
    # depth=1 from a: b + d
    neigh = gs.get_neighbors("a", depth=1)
    names = sorted(n["name"] for n in neigh)
    assert names == ["b", "d"]
    # depth=2 from a: b + c + d
    neigh2 = gs.get_neighbors("a", depth=2)
    assert {n["name"] for n in neigh2} == {"b", "c", "d"}


def test_unknown_predicate_raises(tmp_path: Path):
    gs = GraphStore(tmp_path / "x.kuzu")
    with pytest.raises(GraphStoreError, match="Unknown predicate"):
        gs.upsert_triples([Triple("a", "bogus_rel", "b")])


def test_tagged_with_creates_tag_and_edge(tmp_path: Path):
    gs = GraphStore(tmp_path / "x.kuzu")
    gs.upsert_triples([
        Triple("wiki/concepts/foo", "tagged_with", "llm"),
        Triple("wiki/concepts/foo", "tagged_with", "vercel"),
    ])
    s = gs.stats()
    assert s["pages"] == 1
    assert s["tags"] == 2
    assert s["tagged_with"] == 2


def test_produced_in_creates_episode(tmp_path: Path):
    gs = GraphStore(tmp_path / "x.kuzu")
    gs.upsert_triples([
        Triple("wiki/concepts/foo", "produced_in", "cc:2026-04-19-foo")
    ])
    s = gs.stats()
    assert s["episodes"] == 1
    assert s["produced_in"] == 1


# ----- extract ----------------------------------------------------------------

def _ir(rel: str, *, fm: dict | None = None, links=None, body: str = "") -> dict:
    return {
        "relative_path": rel,
        "source_path": f"/tmp/{rel}",
        "frontmatter": fm or {},
        "wiki_links": links or [],
        "outbound_urls": [],
        "content_md": body,
    }


def test_extract_wiki_links_become_references():
    ir = _ir(
        "wiki/concepts/foo.md",
        links=["wiki/concepts/bar", "wiki/concepts/baz.md"],
    )
    triples = extract_triples(ir)
    refs = [t for t in triples if t.predicate == "references_"]
    targets = sorted(t.object for t in refs)
    assert targets == ["wiki/concepts/bar", "wiki/concepts/baz"]


def test_extract_skips_self_loops():
    ir = _ir("wiki/concepts/foo.md", links=["wiki/concepts/foo"])
    triples = extract_triples(ir)
    assert all(t.object != "wiki/concepts/foo" for t in triples
               if t.predicate == "references_")


def test_extract_frontmatter_related_and_sources():
    ir = _ir(
        "wiki/concepts/foo.md",
        fm={
            "related": ["wiki/concepts/bar"],
            "sources": ["raw-sources/article.md"],
        },
    )
    triples = extract_triples(ir)
    kinds = {(t.object, t.properties.get("kind")) for t in triples
             if t.predicate == "references_"}
    assert ("wiki/concepts/bar", "frontmatter-related") in kinds
    assert ("raw-sources/article", "cites") in kinds


def test_extract_tags_become_tagged_with():
    ir = _ir(
        "wiki/concepts/foo.md",
        fm={"tags": ["llm", "vercel", "  "]},  # whitespace-only filtered
    )
    triples = extract_triples(ir)
    tags = sorted(t.object for t in triples if t.predicate == "tagged_with")
    assert tags == ["llm", "vercel"]


def test_extract_session_id_becomes_produced_in():
    ir = _ir(
        "wiki/concepts/foo.md",
        fm={"session_id": "cc:2026-04-19-foo"},
    )
    triples = extract_triples(ir)
    eps = [t for t in triples if t.predicate == "produced_in"]
    assert len(eps) == 1
    assert eps[0].object == "cc:2026-04-19-foo"


def test_extract_handles_empty_ir():
    ir = _ir("empty.md")
    triples = extract_triples(ir)
    assert triples == []


def test_extract_llm_deep_not_implemented():
    ir = _ir("foo.md")
    with pytest.raises(NotImplementedError, match="v0.55"):
        extract_triples(ir, mode=ExtractionMode.LLM_DEEP)


# ----- end-to-end: extract → store --------------------------------------------

def test_e2e_real_kb_file(tmp_path: Path):
    """End-to-end: a realistic KB file → triples → graph DB → query."""
    ir = _ir(
        "wiki/howtos/cross-platform-memory-spec.md",
        fm={
            "type": "howto",
            "tags": ["memory", "schema", "cross-platform"],
            "related": ["wiki/concepts/memory-architecture"],
            "sources": [],
            "session_id": "cc:2026-04-19-cross-platform-memory-spec",
        },
        links=["wiki/howtos/memory-spec-for-chatgpt",
               "wiki/howtos/memory-spec-for-codex"],
    )
    triples = extract_triples(ir)
    gs = GraphStore(tmp_path / "x.kuzu")
    gs.upsert_episode("cc:2026-04-19-cross-platform-memory-spec")
    n = gs.upsert_triples(triples)
    assert n == len(triples)

    # Now query: what does the spec page reference?
    neigh = gs.get_neighbors("wiki/howtos/cross-platform-memory-spec", depth=1)
    names = {n["name"] for n in neigh}
    assert "wiki/howtos/memory-spec-for-chatgpt" in names
    assert "wiki/howtos/memory-spec-for-codex" in names
    assert "wiki/concepts/memory-architecture" in names
