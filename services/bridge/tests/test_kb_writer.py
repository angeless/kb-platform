"""Tests for bridge.writers.kb_writer.

Uses a temporary git repo as a fake Hogwarts-KB. Auto-push is disabled in
tests (we only verify local commit creation).
"""

from __future__ import annotations

from pathlib import Path

import frontmatter
import pytest
from git import Repo

from bridge.writers.kb_writer import (
    GitLockTimeout,
    KBWriteError,
    write_analysis_to_kb,
    write_summary_to_kb,
    _check_path_allowed,
    _slugify,
    _wait_for_git_lock,
)


# ----- helpers ----------------------------------------------------------------

def _init_fake_kb(root: Path) -> Repo:
    """Create a git repo at root with the standard KB folder layout + initial commit."""
    repo = Repo.init(root)
    # Configure identity for the test commits
    with repo.config_writer() as cfg:
        cfg.set_value("user", "name", "Test User")
        cfg.set_value("user", "email", "test@example.local")
    # Seed minimal layout
    for sub in ["wiki/summaries", "wiki/analyses", "raw-sources", "lessons"]:
        (root / sub).mkdir(parents=True, exist_ok=True)
        (root / sub / ".gitkeep").touch()
    repo.git.add("--all")
    repo.index.commit("initial layout")
    return repo


@pytest.fixture()
def fake_kb(tmp_path: Path, monkeypatch):
    """Build a fake KB + patch get_settings() to point at it."""
    repo = _init_fake_kb(tmp_path)
    from bridge import config as bridge_config
    from bridge.writers import kb_writer

    class FakeSettings:
        hogwarts_kb_path = tmp_path
        hogwarts_kb_branch = repo.active_branch.name
        hogwarts_kb_auto_push = False
        writer_allowed_paths = ["wiki/summaries", "wiki/analyses"]
        writer_git_lock_timeout_s = 2

    monkeypatch.setattr(bridge_config, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(kb_writer, "get_settings", lambda: FakeSettings())
    return tmp_path, repo


# ----- _slugify ---------------------------------------------------------------

@pytest.mark.parametrize(
    "input_,expected",
    [
        ("Hello World", "hello-world"),
        ("中文 标题 测试", "中文-标题-测试"),
        ("Mixed 中英 Title", "mixed-中英-title"),
        ("--leading--trailing--", "leading--trailing"),
        ("", "untitled"),
        ("Special!@#chars", "specialchars"),
    ],
)
def test_slugify(input_, expected):
    assert _slugify(input_) == expected


# ----- _check_path_allowed ----------------------------------------------------

def test_check_path_allowed_accepts_inside_summary(tmp_path):
    target = tmp_path / "wiki" / "summaries" / "x.md"
    _check_path_allowed(target, tmp_path, ["wiki/summaries"])  # no raise


def test_check_path_allowed_rejects_raw_sources(tmp_path):
    target = tmp_path / "raw-sources" / "x.md"
    with pytest.raises(KBWriteError, match="not in"):
        _check_path_allowed(target, tmp_path, ["wiki/summaries", "wiki/analyses"])


def test_check_path_allowed_rejects_lessons(tmp_path):
    target = tmp_path / "lessons" / "x.md"
    with pytest.raises(KBWriteError, match="not in"):
        _check_path_allowed(target, tmp_path, ["wiki/summaries", "wiki/analyses"])


# ----- _wait_for_git_lock -----------------------------------------------------

def test_wait_for_git_lock_no_lock_returns_immediately(tmp_path):
    (tmp_path / ".git").mkdir()
    _wait_for_git_lock(tmp_path, timeout_s=2)  # no raise


def test_wait_for_git_lock_times_out(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "index.lock").touch()
    with pytest.raises(GitLockTimeout):
        _wait_for_git_lock(tmp_path, timeout_s=1)


# ----- write_summary_to_kb ----------------------------------------------------

def test_write_summary_creates_file_and_commit(fake_kb):
    kb_root, repo = fake_kb
    res = write_summary_to_kb(
        title="Test Summary",
        body="The first sentence.\n\nThe second sentence.\n",
        sources=["raw-sources/article.md"],
        tags=["test", "summary"],
    )
    target = kb_root / res["path"]
    assert target.exists()
    assert res["path"] == "wiki/summaries/test-summary.md"
    assert res["wrote_bytes"] > 0
    assert res["auto_pushed"] is False

    # Frontmatter validity (per Hogwarts-KB SCHEMA.md + CLAUDE.md p-chain rule)
    post = frontmatter.loads(target.read_text(encoding="utf-8"))
    assert post.metadata["title"] == "Test Summary"
    assert post.metadata["type"] == "summary"
    assert post.metadata["updated_by"] == "kbsql-bridge[bot]"
    assert post.metadata["sources"] == ["raw-sources/article.md"]
    assert "test" in post.metadata["tags"]
    # CLAUDE.md mandate: session_id with `cc:` channel prefix for kb-index.py
    assert post.metadata["session_id"].startswith("cc:")
    assert "test-summary" in post.metadata["session_id"]
    assert post.metadata["source"] == "claude-code-bridge"
    assert post.metadata["parent_session_id"] is None

    # Commit landed with bridge bot identity
    last = repo.head.commit
    assert "bridge: add/update summary — Test Summary" in last.message
    assert "wiki/summaries/test-summary.md" in last.stats.files
    assert last.author.name == "kbsql-bridge[bot]"
    assert last.author.email == "bridge@kb-platform.local"
    assert last.committer.name == "kbsql-bridge[bot]"


def test_write_analysis_creates_file_in_analyses_folder(fake_kb):
    kb_root, repo = fake_kb
    res = write_analysis_to_kb(
        title="Tool Analysis",
        body="Detailed comparison body.\n",
    )
    target = kb_root / res["path"]
    assert target.exists()
    assert res["path"] == "wiki/analyses/tool-analysis.md"
    post = frontmatter.loads(target.read_text(encoding="utf-8"))
    assert post.metadata["type"] == "analysis"


def test_write_idempotent_no_second_commit(fake_kb):
    kb_root, repo = fake_kb
    initial_commit_count = sum(1 for _ in repo.iter_commits())
    res1 = write_summary_to_kb(title="Same", body="Body.\n")
    after_first = sum(1 for _ in repo.iter_commits())
    assert after_first == initial_commit_count + 1

    # Same write again — file content identical → no new commit (frontmatter dates same)
    res2 = write_summary_to_kb(title="Same", body="Body.\n")
    after_second = sum(1 for _ in repo.iter_commits())
    # Note: 'created' / 'updated' dates are date.today() so on same day → no diff → no commit
    assert after_second == after_first
    assert res1["path"] == res2["path"]


def test_write_refused_when_path_outside_allowed(fake_kb, monkeypatch):
    """Confirm that even if subdir param is forced to 'lessons/', it bails."""
    from bridge.writers import kb_writer

    # Manually invoke _write_internal with an illegal subdir
    with pytest.raises(KBWriteError, match="not in"):
        kb_writer._write_internal(
            page_type="lesson",
            subdir="lessons",
            title="bad",
            body="body",
            sources=None,
            related=None,
            tags=None,
            slug=None,
            extra_frontmatter=None,
            commit_message="bridge: bad",
        )


def test_write_fails_when_kb_path_not_a_repo(tmp_path, monkeypatch):
    """If the KB path isn't a git repo, bridge refuses."""
    from bridge import config as bridge_config
    from bridge.writers import kb_writer

    class FakeSettings:
        hogwarts_kb_path = tmp_path
        hogwarts_kb_branch = "main"
        hogwarts_kb_auto_push = False
        writer_allowed_paths = ["wiki/summaries"]
        writer_git_lock_timeout_s = 1

    monkeypatch.setattr(bridge_config, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(kb_writer, "get_settings", lambda: FakeSettings())

    with pytest.raises(KBWriteError, match="not a git repo"):
        write_summary_to_kb(title="x", body="y\n")


# =================================================================
# v0.54 — augment_existing_in_place tests
# =================================================================

from bridge.writers.kb_writer import augment_existing_in_place


def test_augment_in_place_writes_when_marker_present(fake_kb):
    kb_root, repo = fake_kb
    # Create an existing wiki/howtos file
    target = kb_root / "wiki" / "howtos" / "test.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    original = "# Title\n\nOriginal body.\n"
    target.write_text(original, encoding="utf-8")
    repo.git.add("--all")
    repo.index.commit("seed file")

    augmented = (
        "# Title\n\n"
        "<!-- bridge-visual:start v=1 audience=0.7 -->\n"
        "```mermaid\nflowchart TD\nA-->B\n```\n"
        "<!-- bridge-visual:end -->\n\n"
        "Original body.\n"
    )
    res = augment_existing_in_place(
        relative_path="wiki/howtos/test.md",
        augmented_full_text=augmented,
    )
    assert res["skipped"] is False
    assert (kb_root / "wiki" / "howtos" / "test.md").read_text() == augmented


def test_augment_in_place_skipped_when_unchanged(fake_kb):
    kb_root, repo = fake_kb
    target = kb_root / "wiki" / "howtos" / "test.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    augmented = (
        "# Title\n\n"
        "<!-- bridge-visual:start v=1 audience=0.7 -->\n"
        "<!-- bridge-visual:end -->\n"
    )
    target.write_text(augmented, encoding="utf-8")
    repo.git.add("--all")
    repo.index.commit("seed already-augmented file")

    res = augment_existing_in_place(
        relative_path="wiki/howtos/test.md",
        augmented_full_text=augmented,
    )
    assert res["skipped"] is True
    assert res["wrote_bytes"] == 0


def test_augment_in_place_rejects_missing_marker(fake_kb):
    kb_root, repo = fake_kb
    target = kb_root / "wiki" / "howtos" / "test.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Title\nOriginal\n", encoding="utf-8")
    repo.git.add("--all")
    repo.index.commit("seed")

    with pytest.raises(KBWriteError, match="missing bridge-visual marker"):
        augment_existing_in_place(
            relative_path="wiki/howtos/test.md",
            augmented_full_text="# Title\n\nNo marker here.\n",
        )


def test_augment_in_place_rejects_non_markdown(fake_kb):
    with pytest.raises(KBWriteError, match="only .md files"):
        augment_existing_in_place(
            relative_path="wiki/howtos/test.txt",
            augmented_full_text="<!-- bridge-visual:start -->\n<!-- bridge-visual:end -->",
        )


def test_augment_in_place_rejects_path_traversal(fake_kb):
    with pytest.raises(KBWriteError, match="escapes KB root"):
        augment_existing_in_place(
            relative_path="../../etc/passwd.md",
            augmented_full_text="<!-- bridge-visual:start -->\nx\n<!-- bridge-visual:end -->",
        )


def test_augment_in_place_rejects_nonexistent(fake_kb):
    with pytest.raises(KBWriteError, match="does not exist"):
        augment_existing_in_place(
            relative_path="wiki/howtos/never-existed.md",
            augmented_full_text=(
                "<!-- bridge-visual:start v=1 -->\n"
                "<!-- bridge-visual:end -->\n"
            ),
        )
