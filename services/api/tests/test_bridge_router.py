"""Integration tests for /v1/bridge/* endpoints.

These tests use FastAPI's TestClient with the real app, but the bridge
write endpoints work against a temporary git repo (NOT the real Hogwarts-KB).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from git import Repo

from app.main import create_app


@pytest.fixture()
def client():
    """TestClient that satisfies the CsrfMiddleware (X-Requested-With required for POST)."""
    c = TestClient(create_app())
    c.headers.update({"X-Requested-With": "XMLHttpRequest"})
    return c


@pytest.fixture()
def fake_kb(tmp_path: Path, monkeypatch):
    """Spin up a tiny git repo and point bridge config at it."""
    repo = Repo.init(tmp_path)
    with repo.config_writer() as cfg:
        cfg.set_value("user", "name", "Test")
        cfg.set_value("user", "email", "test@example.local")
    for sub in ["wiki/summaries", "wiki/analyses"]:
        d = tmp_path / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch()
    repo.git.add("--all")
    repo.index.commit("initial")

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
        bridge_llm_base_url = "https://example.test"
        writer_allowed_paths = ["wiki/summaries", "wiki/analyses"]
        writer_git_lock_timeout_s = 1
        watcher_ignore_globs = [".git/*"]

    monkeypatch.setattr(bridge_config, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(kb_writer, "get_settings", lambda: FakeSettings())
    return tmp_path


# ----- read-only endpoints ----------------------------------------------------

def test_bridge_health_returns_ok(client):
    r = client.get("/v1/bridge/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_bridge_status_returns_config_snapshot(client, fake_kb):
    r = client.get("/v1/bridge/status")
    assert r.status_code == 200
    body = r.json()
    assert body["bridge_version"]
    assert body["kb_exists"] is True
    assert body["llm_provider"] == "glm"
    assert body["llm_strict"] is True
    assert body["glm_key_configured"] is True


# ----- summarize / classify ---------------------------------------------------

def test_summarize_extractive_no_llm(client):
    long_text = (
        "The quick brown fox jumps over the lazy dog. "
        "Machine learning models extract patterns from data. "
        "Bridge services synchronize knowledge bases. "
        "Each parser handles a specific file format. "
        "Tests verify expected behavior automatically."
    )
    r = client.post("/v1/bridge/summarize", json={
        "text": long_text,
        "target_chars": 100,
        "max_sentences": 2,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["sentence_count"] >= 1
    assert body["method"].startswith("lexrank") or body["method"] == "fallback-truncate"


def test_summarize_rejects_empty_text(client):
    r = client.post("/v1/bridge/summarize", json={"text": ""})
    assert r.status_code == 422  # pydantic validation


def test_classify_returns_page_type(client):
    r = client.post("/v1/bridge/classify", json={
        "body": "## Step 1: Install. ## Step 2: Configure.",
        "title_hint": "Setup",
    })
    assert r.status_code == 200
    body = r.json()
    # The hint count should land on howto
    assert body["page_type"] in {"howto", "concept"}
    assert body["suggested_path"].startswith("wiki/")


# ----- ingest -----------------------------------------------------------------

def test_ingest_returns_404_when_file_missing(client, fake_kb):
    r = client.post("/v1/bridge/ingest", json={"path": "wiki/concepts/missing.md"})
    assert r.status_code == 404


def test_ingest_parses_existing_md_file(client, fake_kb):
    f = fake_kb / "wiki" / "concepts"
    f.mkdir(parents=True, exist_ok=True)
    (f / "real.md").write_text("# Real Title\n\nBody.\n", encoding="utf-8")
    r = client.post("/v1/bridge/ingest", json={"path": "wiki/concepts/real.md"})
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "markdown"
    assert body["kb_layer"] == "wiki"
    assert body["relative_path"] == "wiki/concepts/real.md"
    assert len(body["content_hash"]) == 64


def test_ingest_rejects_unsupported_extension(client, fake_kb):
    f = fake_kb / "weird.xyz"
    f.write_text("noise", encoding="utf-8")
    r = client.post("/v1/bridge/ingest", json={"path": str(f)})
    assert r.status_code == 415


def test_ingest_path_traversal_rejected(client, fake_kb):
    """Cross-audit Stage 2 H2 fix: REST /ingest must guard against ../../etc/passwd."""
    # Try to escape the KB root
    r = client.post("/v1/bridge/ingest", json={"path": "../../etc/passwd"})
    assert r.status_code == 403
    assert "escapes KB root" in r.json()["detail"]


def test_ingest_absolute_path_outside_kb_rejected(client, fake_kb, tmp_path):
    """Even an absolute path outside the KB root must be rejected."""
    outside = tmp_path.parent / "outside.md"
    outside.write_text("# Outside\n", encoding="utf-8")
    try:
        r = client.post("/v1/bridge/ingest", json={"path": str(outside)})
        assert r.status_code == 403
    finally:
        outside.unlink(missing_ok=True)


# ----- write endpoints --------------------------------------------------------

def test_write_summary_creates_file_and_commit(client, fake_kb):
    r = client.post("/v1/bridge/write/summary", json={
        "title": "API Test Summary",
        "body": "Body of the summary.\n",
        "tags": ["test"],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["path"] == "wiki/summaries/api-test-summary.md"
    assert body["wrote_bytes"] > 0
    assert body["auto_pushed"] is False
    assert (fake_kb / body["path"]).exists()


def test_write_analysis_creates_file_in_analyses(client, fake_kb):
    r = client.post("/v1/bridge/write/analysis", json={
        "title": "API Test Analysis",
        "body": "Comparison body.\n",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["path"] == "wiki/analyses/api-test-analysis.md"


def test_mappings_endpoint_returns_stub(client):
    r = client.get("/v1/bridge/mappings")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert "v0.53 stub" in body["_note"]
