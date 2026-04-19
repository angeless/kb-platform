"""Tests for bridge.parsers.markdown_parser.

These cover the four Hogwarts-KB layer conventions defined in SCHEMA.md.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from bridge.parsers.markdown_parser import (
    detect_kb_layer,
    parse_markdown,
)


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return p


def test_parse_wiki_concept_with_full_frontmatter(tmp_path: Path) -> None:
    f = _write(
        tmp_path,
        "wiki/concepts/zhipu-models.md",
        """
        ---
        title: "Zhipu Models"
        type: concept
        created: 2026-04-13
        updated: 2026-04-19
        updated_by: claude-code
        sources:
          - raw-sources/zhipu-launch.md
        related:
          - wiki/concepts/glm-4.md
        tags: [llm, zhipu]
        ---

        # Zhipu Models

        Zhipu offers GLM-4 and GLM-4V. See [[wiki/concepts/glm-4]] for details.
        Reference: https://open.bigmodel.cn/dev/api
        """,
    )
    ir = parse_markdown(f)
    assert ir["kind"] == "markdown"
    assert ir["source_format"] == "md"
    assert ir["title"] == "Zhipu Models"  # frontmatter title wins
    assert ir["frontmatter"]["type"] == "concept"
    assert "wiki/concepts/glm-4" in ir["wiki_links"]
    assert "https://open.bigmodel.cn/dev/api" in ir["outbound_urls"]
    assert ir["content_hash"]
    assert ir["raw_size"] > 0


def test_title_falls_back_to_h1(tmp_path: Path) -> None:
    f = _write(
        tmp_path,
        "no-fm.md",
        """
        # Plain Heading Title

        Body text.
        """,
    )
    ir = parse_markdown(f)
    assert ir["title"] == "Plain Heading Title"
    assert ir["frontmatter"] == {}


def test_title_falls_back_to_filename_stem(tmp_path: Path) -> None:
    f = _write(
        tmp_path,
        "weird-doc.md",
        """
        Just a paragraph, no heading.
        """,
    )
    ir = parse_markdown(f)
    assert ir["title"] == "weird-doc"


def test_wiki_link_with_alias_extracts_target_only(tmp_path: Path) -> None:
    f = _write(
        tmp_path,
        "links.md",
        """
        # Links

        See [[wiki/concepts/page|the page]] for more.
        """,
    )
    ir = parse_markdown(f)
    assert ir["wiki_links"] == ["wiki/concepts/page"]


def test_outbound_urls_dedup_and_strip_trailing_punct(tmp_path: Path) -> None:
    f = _write(
        tmp_path,
        "urls.md",
        """
        # URLs

        First [link](https://example.com/page).
        Bare: https://example.com/page, also https://other.com/x.
        """,
    )
    ir = parse_markdown(f)
    # markdown link URL keeps the path, bare URL strips trailing comma
    assert "https://example.com/page" in ir["outbound_urls"]
    assert "https://other.com/x" in ir["outbound_urls"]
    # No duplicate
    assert ir["outbound_urls"].count("https://example.com/page") == 1


def test_content_hash_is_deterministic(tmp_path: Path) -> None:
    f1 = _write(tmp_path, "a.md", "# Same Body\n\ntext.\n")
    f2 = _write(tmp_path, "b.md", "# Same Body\n\ntext.\n")
    assert parse_markdown(f1)["content_hash"] == parse_markdown(f2)["content_hash"]


def test_empty_file_raises(tmp_path: Path) -> None:
    f = tmp_path / "empty.md"
    f.write_bytes(b"")
    with pytest.raises(ValueError, match="Empty file"):
        parse_markdown(f)


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_markdown(tmp_path / "nope.md")


def test_non_utf8_raises(tmp_path: Path) -> None:
    f = tmp_path / "bin.md"
    f.write_bytes(b"\xff\xfe not utf-8")
    with pytest.raises(ValueError, match="not UTF-8"):
        parse_markdown(f)


@pytest.mark.parametrize(
    "rel,expected",
    [
        ("raw-sources/x.md", "raw-sources"),
        ("wiki/concepts/y.md", "wiki"),
        ("lessons/2026-04-19-z.md", "lessons"),
        ("memory/feedback_x.md", "memory"),
        ("INDEX.md", "unknown"),
        ("randomdir/file.md", "unknown"),
    ],
)
def test_detect_kb_layer(tmp_path: Path, rel: str, expected: str) -> None:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("hi", encoding="utf-8")
    assert detect_kb_layer(p, tmp_path) == expected


def test_detect_kb_layer_outside_root_returns_unknown(tmp_path: Path) -> None:
    other = tmp_path.parent / "elsewhere.md"
    other.write_text("hi", encoding="utf-8")
    try:
        assert detect_kb_layer(other, tmp_path) == "unknown"
    finally:
        other.unlink(missing_ok=True)
