"""MCP server tool tests.

We test the tool functions directly (not via mcp protocol round-trip)
because the FastMCP decorator wraps them but exposes the original
callable on the registry. This gives faster, hermetic unit tests.

Protocol round-trip tests (stdio JSON-RPC) belong in v0.54 — they need
mcp's test client setup which is more complex.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from git import Repo

from mcp_server.server import mcp


# ----- helpers ----------------------------------------------------------------

def _init_fake_kb(root: Path) -> Repo:
    repo = Repo.init(root)
    with repo.config_writer() as cfg:
        cfg.set_value("user", "name", "Test")
        cfg.set_value("user", "email", "t@t.local")
    for sub in ["wiki/concepts", "wiki/summaries", "wiki/analyses", "raw-sources"]:
        d = root / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch()
    (root / "wiki" / "concepts" / "vercel.md").write_text(
        "---\ntitle: Vercel\ntype: concept\n---\n\n# Vercel\n\n"
        "Vercel is a deployment platform. See [[wiki/concepts/nextjs]].\n",
        encoding="utf-8",
    )
    (root / "wiki" / "concepts" / "nextjs.md").write_text(
        "# Next.js\n\nReact framework.\n", encoding="utf-8",
    )
    (root / "raw-sources" / "article.md").write_text(
        "---\ntitle: Article\nsource: https://x.com\n---\n\nText.\n",
        encoding="utf-8",
    )
    repo.git.add("--all")
    repo.index.commit("initial")
    return repo


@pytest.fixture()
def fake_kb(tmp_path: Path, monkeypatch):
    repo = _init_fake_kb(tmp_path)
    from bridge import config as bridge_config
    from bridge.writers import kb_writer

    class FakeSettings:
        hogwarts_kb_path = tmp_path
        hogwarts_kb_branch = repo.active_branch.name
        hogwarts_kb_auto_push = False
        glm_api_key = "test-key"
        bridge_llm_provider = "glm"
        bridge_llm_strict = True
        bridge_llm_model = "glm-4-flash"
        bridge_llm_base_url = "https://x.test"
        writer_allowed_paths = ["wiki/summaries", "wiki/analyses"]
        writer_git_lock_timeout_s = 1
        watcher_ignore_globs = [".git/*", ".obsidian/*"]

    monkeypatch.setattr(bridge_config, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(kb_writer, "get_settings", lambda: FakeSettings())
    return tmp_path


def _get_tool(name: str):
    """Look up a tool's underlying callable from the FastMCP registry."""
    # FastMCP stores tool definitions; the .fn attribute is the original callable
    for tool in mcp._tool_manager.list_tools():
        if tool.name == name:
            return tool.fn
    raise KeyError(f"Tool not found: {name}")


# ----- tool inventory ---------------------------------------------------------

def test_all_expected_tools_registered():
    """Confirm all 8 v0.53 tools are registered."""
    expected = {
        "kb_status",
        "kb_search",
        "kb_read",
        "kb_ingest",
        "kb_summarize",
        "kb_classify",
        "kb_write_summary",
        "kb_write_analysis",
    }
    actual = {t.name for t in mcp._tool_manager.list_tools()}
    missing = expected - actual
    assert not missing, f"Missing tools: {missing}"


# ----- read-only tool tests ---------------------------------------------------

def test_kb_status(fake_kb):
    fn = _get_tool("kb_status")
    res = fn()
    assert res["llm_provider"] == "glm"
    assert res["llm_strict"] is True
    assert res["kb_exists"] is True
    assert res["glm_key_configured"] is True


def test_kb_search_finds_concept(fake_kb):
    fn = _get_tool("kb_search")
    res = fn("vercel")
    assert len(res) >= 1
    paths = [r["relative_path"] for r in res]
    assert "wiki/concepts/vercel.md" in paths
    # Snippet should reference the matched term
    top = res[0]
    assert top["match_count"] > 0


def test_kb_search_returns_empty_when_no_match(fake_kb):
    fn = _get_tool("kb_search")
    res = fn("nonexistentterm9999")
    assert res == []


def test_kb_read_returns_content_and_frontmatter(fake_kb):
    fn = _get_tool("kb_read")
    res = fn("wiki/concepts/vercel.md")
    assert "error" not in res
    assert res["frontmatter"]["title"] == "Vercel"
    assert "Vercel is a deployment" in res["content"]


def test_kb_read_path_traversal_rejected(fake_kb):
    fn = _get_tool("kb_read")
    res = fn("../../etc/passwd")
    assert "error" in res
    assert "escapes KB root" in res["error"] or "not found" in res["error"].lower()


def test_kb_read_missing_file_returns_error(fake_kb):
    fn = _get_tool("kb_read")
    res = fn("wiki/concepts/nope.md")
    assert "error" in res


def test_kb_ingest_parses_md(fake_kb):
    fn = _get_tool("kb_ingest")
    res = fn("wiki/concepts/vercel.md")
    assert "error" not in res
    assert res["kind"] == "markdown"
    assert res["kb_layer"] == "wiki"


def test_kb_summarize(fake_kb):
    fn = _get_tool("kb_summarize")
    text = (
        "Sentence one is here. Sentence two follows along. "
        "Sentence three rounds it out. Sentence four is the final."
    )
    res = fn(text, target_chars=100, max_sentences=2)
    assert "method" in res
    assert res["sentence_count"] >= 1


def test_kb_classify(fake_kb):
    fn = _get_tool("kb_classify")
    res = fn("## Step 1: Install. ## Step 2: Configure.", title_hint="Setup")
    assert res["page_type"] in {"howto", "concept"}
    assert res["suggested_path"].startswith("wiki/")


# ----- write tool tests -------------------------------------------------------

def test_kb_write_summary_creates_file(fake_kb):
    fn = _get_tool("kb_write_summary")
    res = fn(title="MCP Test", body="Body via MCP.\n", tags=["mcp"])
    assert "error" not in res
    assert res["path"] == "wiki/summaries/mcp-test.md"
    assert (fake_kb / res["path"]).exists()


def test_kb_write_analysis_creates_file(fake_kb):
    fn = _get_tool("kb_write_analysis")
    res = fn(title="MCP Analysis", body="Comparison body.\n")
    assert "error" not in res
    assert res["path"] == "wiki/analyses/mcp-analysis.md"
