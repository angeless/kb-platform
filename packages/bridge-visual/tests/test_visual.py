"""Tests for bridge_visual: profile + outline + mermaid + augment."""

from __future__ import annotations

import textwrap

import pytest

from bridge_visual import (
    AUDIENCE_HUMAN_THRESHOLD_DEFAULT,
    augment_markdown,
    generate_mermaid,
    generate_outline,
    profile_reader,
)
from bridge_visual.profile import ReaderProfile


# ----- profile_reader ---------------------------------------------------------

def test_profile_short_data_dump_low_score():
    text = "name,age\nAlice,30\nBob,25\n"
    p = profile_reader(text)
    assert p.audience_score < 0.3
    assert not p.has_steps
    assert not p.has_outline_value


def test_profile_howto_with_steps_high_score():
    text = textwrap.dedent("""
        ---
        type: howto
        ---

        # Setup Guide

        ## Step 1: Install dependencies

        Run npm install.

        ## Step 2: Configure environment

        Edit .env.

        ## Step 3: Start service

        npm run dev.
    """).strip()
    p = profile_reader(text)
    assert p.has_steps is True
    assert p.audience_score >= 0.4  # type=howto + steps


def test_profile_long_concept_with_outline():
    text = "---\ntype: concept\n---\n\n# Title\n\n" + (
        "## Section A\n\n" + "lorem ipsum " * 100 + "\n\n" +
        "## Section B\n\n" + "lorem ipsum " * 100 + "\n\n" +
        "## Section C\n\n" + "lorem ipsum " * 100 + "\n\n" +
        "## Section D\n\n" + "lorem ipsum " * 100 + "\n\n" +
        "## Section E\n\n" + "lorem ipsum " * 100 + "\n"
    )
    p = profile_reader(text)
    assert p.has_outline_value is True
    assert p.heading_count >= 5
    assert p.audience_score >= 0.35


def test_profile_state_machine_detected():
    text = "# State machine\n\nidle --> ready\nready --> processing\nprocessing --> done\n"
    p = profile_reader(text)
    assert p.has_state_machine is True


def test_profile_branches_detected():
    text = "# Decision\n\nIf the user is admin then grant access. " \
           "If the user is guest then deny.\n"
    p = profile_reader(text)
    assert p.has_branches is True


def test_profile_chinese_steps():
    text = textwrap.dedent("""
        # 中文教程

        ## 第一步: 准备
        准备工作。

        ## 第二步: 配置
        配置说明。

        ## 第三步: 部署
        部署流程。
    """).strip()
    p = profile_reader(text)
    assert p.has_steps is True


def test_profile_returns_rationale_dict():
    text = "## Step 1: foo\n## Step 2: bar\n"
    p = profile_reader(text)
    assert "steps" in p.rationale
    assert p.rationale["steps"] > 0


# ----- generate_outline -------------------------------------------------------

def test_outline_returns_none_for_few_headings():
    body = "# Just one\n\nbody"
    assert generate_outline(body, min_headings=3) is None


def test_outline_with_nested_headings():
    body = textwrap.dedent("""
        # Main
        ## Section A
        ### Subsection A1
        ## Section B
        ### Subsection B1
    """).strip()
    out = generate_outline(body, min_headings=3)
    assert out is not None
    assert "<details>" in out
    assert "</details>" in out
    assert "[Main](#main)" in out
    assert "[Section A](#section-a)" in out
    assert "  - [Subsection A1](#subsection-a1)" in out  # nested indent


def test_outline_chinese_anchors():
    body = "## 第一节\n## 第二节\n## 第三节\n"
    out = generate_outline(body, min_headings=3)
    assert out is not None
    assert "[第一节](#第一节)" in out


# ----- generate_mermaid -------------------------------------------------------

def test_mermaid_returns_flowchart_for_steps():
    body = textwrap.dedent("""
        ## Step 1: First
        Body.

        ## Step 2: Second
        Body.

        ## Step 3: Third
        Body.
    """).strip()
    p = profile_reader(body)
    diag = generate_mermaid(p, body)
    assert diag is not None
    assert diag.kind == "flowchart"
    assert "flowchart TD" in diag.code
    assert "Step 1" in diag.code
    assert "n0 --> n1" in diag.code


def test_mermaid_returns_state_diagram_for_transitions():
    body = "## State machine\n\nidle --> ready\nready --> done\n"
    p = profile_reader(body)
    diag = generate_mermaid(p, body)
    if diag is not None:
        # When detected, it's a stateDiagram
        assert diag.kind == "stateDiagram"
        assert "stateDiagram-v2" in diag.code
        assert "idle --> ready" in diag.code


def test_mermaid_returns_none_for_unstructured_text():
    body = "Just some prose with no clear structure.\n\nAnother paragraph.\n"
    p = profile_reader(body)
    assert generate_mermaid(p, body) is None


# ----- augment_markdown end-to-end --------------------------------------------

def test_augment_skips_low_audience_doc():
    text = "# Notes\nshort body\n"
    res = augment_markdown(text)
    assert res.augmented is False
    assert res.skipped_reason is not None
    assert "audience_score" in res.skipped_reason


def test_augment_inserts_block_for_human_doc():
    # Realistic-length howto with 3 steps + more headings → audience > 0.6
    body_padding = "Detailed explanation paragraph. " * 50
    text = textwrap.dedent(f"""
        ---
        title: Setup Guide
        type: howto
        ---

        # Setup Guide

        ## Overview

        {body_padding}

        ## Step 1: Install

        {body_padding}

        ## Step 2: Configure

        {body_padding}

        ## Step 3: Run

        {body_padding}

        ## Troubleshooting

        {body_padding}
    """).strip() + "\n"
    res = augment_markdown(text)
    assert res.augmented is True, f"profile: {res.profile}"
    assert "<!-- bridge-visual:start" in res.output
    assert "<!-- bridge-visual:end -->" in res.output
    assert "```mermaid" in res.output
    # Original H1 still present + only once
    assert res.output.count("# Setup Guide") == 1
    # Frontmatter preserved
    assert "title: Setup Guide" in res.output


def test_augment_idempotent_replaces_old_block():
    body_padding = "Detailed paragraph content. " * 50
    text = textwrap.dedent(f"""
        ---
        type: howto
        ---

        # Title

        ## Overview

        {body_padding}

        ## Step 1: Foo

        {body_padding}

        ## Step 2: Bar

        {body_padding}

        ## Step 3: Baz

        {body_padding}
    """).strip() + "\n"
    res1 = augment_markdown(text)
    assert res1.augmented is True
    # Re-augment the augmented output: should NOT double-insert
    res2 = augment_markdown(res1.output)
    assert res2.augmented is True
    assert res2.output.count("<!-- bridge-visual:start") == 1
    assert res2.output.count("<!-- bridge-visual:end -->") == 1


def test_augment_below_threshold_strips_stale_block():
    """If a doc was once human-leaning and got augmented, but later edits
    reduced its audience score, the augmenter should strip the stale block."""
    augmented = textwrap.dedent("""
        ---
        type: memory
        ---

        <!-- bridge-visual:start v=1 audience=0.78 -->
        ```mermaid
        flowchart TD
            n0[\"x\"]
        ```
        <!-- bridge-visual:end -->

        Plain notes only.
    """).strip() + "\n"
    res = augment_markdown(augmented)
    assert res.augmented is False
    assert "<!-- bridge-visual:start" not in res.output
    assert "<!-- bridge-visual:end" not in res.output
    # Original substantive content preserved
    assert "Plain notes only." in res.output


def test_augment_threshold_override():
    text = "---\ntype: concept\n---\n\n# Short concept\n"
    # Force threshold to 0.0 — should still skip because no diagram/outline
    res = augment_markdown(text, threshold=0.0)
    assert res.augmented is False
    assert "no diagram or outline" in res.skipped_reason
