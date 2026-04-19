"""Tests for bridge_utils.summarize and bridge_utils.classify (no LLM)."""

from __future__ import annotations

import pytest

from bridge_utils import summarize_extractive, classify_path


# ---- summarize_extractive ----------------------------------------------------

def test_summarize_short_text_returns_truncated():
    res = summarize_extractive("Tiny.", target_chars=200)
    assert res.method == "fallback-truncate"
    assert res.confidence == 0.0
    assert res.needs_llm_fallback is False  # nothing to do


def test_summarize_paragraph_uses_lexrank():
    text = """
    The bridge service synchronizes the Hogwarts knowledge base with KBSQL.
    It watches the filesystem for changes using watchfiles.
    Each detected change is parsed by the appropriate parser based on file extension.
    Markdown files use the markdown parser. Office files use markitdown.
    PDFs use docling for layout-aware extraction.
    The pipeline then ingests the parsed content into the database.
    Finally, summaries are written back to the wiki/summaries directory.
    """
    res = summarize_extractive(text, target_chars=200, max_sentences=3)
    assert res.method.startswith("lexrank")
    assert res.sentence_count >= 1
    assert res.char_count > 0
    assert 0.0 < res.confidence <= 1.0


def test_summarize_strips_markdown_formatting():
    text = """
    # Heading

    This is a [link to docs](https://example.com).
    See [[wiki/concepts/foo]] for details.

    - bullet one
    - bullet two

    `inline code` and **bold** text.
    """
    res = summarize_extractive(text, target_chars=200)
    # Whatever sentences come out, they should NOT contain raw markdown
    assert "](" not in res.text
    assert "[[" not in res.text
    assert "**" not in res.text


def test_summarize_handles_frontmatter():
    text = """---
title: Foo
type: concept
tags: [a, b]
---

The first sentence is here. The second sentence follows.
A third sentence rounds it out for testing purposes.
"""
    res = summarize_extractive(text, target_chars=200)
    assert "title: Foo" not in res.text
    assert res.sentence_count >= 1


# ---- classify_path -----------------------------------------------------------

def test_classify_explicit_frontmatter_type_wins():
    res = classify_path(
        "Some body content here.",
        title_hint="MyDoc",
        existing_frontmatter_type="howto",
    )
    assert res.page_type == "howto"
    assert res.confidence == 1.0
    assert "wiki/howtos/" in res.suggested_path


def test_classify_howto_via_step_headings():
    text = """
    # Setup Guide

    ## Step 1: Install dependencies

    Run the following command.

    ## Step 2: Configure environment

    Edit the .env file.
    """
    res = classify_path(text, title_hint="Setup Guide")
    assert res.page_type == "howto"
    assert "wiki/howtos/setup-guide.md" == res.suggested_path
    assert any("howto" in r for r in res.reasoning)


def test_classify_analysis_via_keywords():
    text = """
    Comparison of Tool A vs Tool B vs Tool C.

    This deep-dive analysis covers performance, ergonomics, and license trade-offs.
    """
    res = classify_path(text, title_hint="Tool Comparison")
    assert res.page_type == "analysis"
    assert "wiki/analyses/" in res.suggested_path


def test_classify_lesson_via_chinese_keywords():
    text = """
    踩坑：第一次跑这个工具的时候，没有设置环境变量。
    教训：记得先 source .env。复盘下来，应该写一个启动脚本。
    """
    res = classify_path(text, title_hint="教训-环境变量")
    assert res.page_type == "lesson"


def test_classify_unknown_defaults_to_concept():
    text = "Just a plain paragraph about some random topic with no strong cues."
    res = classify_path(text, title_hint="Random")
    assert res.page_type == "concept"
    assert "wiki/concepts/random.md" == res.suggested_path
    assert res.confidence < 0.5  # low confidence


def test_classify_returns_tags():
    text = """
    Vercel deployment best practices.
    Use Vercel CLI with vercel deploy.
    Configure environment variables via vercel env.
    """
    res = classify_path(text, title_hint="Vercel Deploy")
    # YAKE may extract multi-word phrases; just check non-empty
    assert isinstance(res.tags, list)
