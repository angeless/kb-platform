"""Reader profiler — score a markdown article on the human↔AI axis.

Output: ReaderProfile with:
  - audience_score (0.0 = pure AI/data dump, 1.0 = pure human/showcase)
  - has_steps     — has procedural step structure
  - has_branches  — contains decision/conditional language
  - has_state_machine — references states/state transitions
  - has_outline_value — long enough to benefit from a TOC

The score is a weighted sum of independent signals (each 0-1):

  Signal                         Weight  Rationale
  ──────────────────────────────────────────────────────────────────────
  frontmatter type               0.20    howto/concept/analysis lean human;
                                         memory/raw-source lean AI
  H2 step structure              0.20    "## Step N", "## 第N步"
  decision / branch language     0.15    if/then/else, 决策, 选择
  state machine vocabulary       0.10    state, transition, 状态, 流转
  doc length (>3000 chars)       0.15    long docs benefit from outline
  table-of-contents potential    0.10    has ≥5 H2/H3 headings
  visual cue density             0.10    diagrams mentioned, "see figure"

All cumulative; capped at 1.0.

The profiler is **deterministic and side-effect-free** — no LLM, no DB.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import frontmatter

AUDIENCE_HUMAN_THRESHOLD_DEFAULT = 0.6


@dataclass(frozen=True)
class ReaderProfile:
    audience_score: float
    has_steps: bool
    has_branches: bool
    has_state_machine: bool
    has_outline_value: bool
    heading_count: int
    char_count: int
    rationale: dict[str, float]  # signal name → contribution


# Type → score (higher = more human-leaning)
_TYPE_BIAS = {
    "howto": 0.20,
    "analysis": 0.18,
    "concept": 0.12,
    "summary": 0.10,
    "entity": 0.08,
    "memory": 0.0,
    "raw-source": 0.0,
}

_STEP_PATTERNS = [
    r"^##\s+(?:Step|step)\s*\d+",        # "## Step 1"
    r"^##\s+第[一二三四五六七八九十\d]+步",  # "## 第一步"
    r"^##\s*\d+\.\s",                     # "## 1. " "## 2. "
]

_BRANCH_PATTERNS = [
    r"\bif\b\s+.+\s+\bthen\b",
    r"\bwhen\b\s+.+\s+\b(do|use|apply)\b",
    r"如果.+则",
    r"决策树?",
    r"判别|判断|分支|选择",
]

_STATE_MACHINE_PATTERNS = [
    r"\bstate\b\s+(diagram|machine|chart)",
    r"\btransition(s|ed|ing)?\b",
    r"\b(idle|pending|ready|error|done|started|finished)\b\s*(?:→|->|-->)",
    r"状态机|状态流转|状态转移",
]

_VISUAL_CUE_PATTERNS = [
    r"\bsee (figure|diagram|chart|graph)\b",
    r"\b(flowchart|architecture)\s+(diagram|figure)?\b",
    r"参见.*(图|示意)",
    r"```(mermaid|dot|plantuml|graphviz)\b",
]


def _count_pattern_hits(patterns: list[str], text: str, *, multiline: bool = False) -> int:
    flags = re.IGNORECASE | re.MULTILINE
    return sum(len(re.findall(p, text, flags)) for p in patterns)


def _strip_frontmatter(markdown_text: str) -> tuple[dict, str]:
    try:
        post = frontmatter.loads(markdown_text)
        return dict(post.metadata), post.content or ""
    except Exception:
        return {}, markdown_text


def profile_reader(ir_or_markdown: dict[str, Any] | str) -> ReaderProfile:
    """Score the human-readability of a markdown article.

    Args:
        ir_or_markdown: bridge IR dict OR raw markdown string

    Returns:
        ReaderProfile with audience_score in [0, 1] + structural flags +
        rationale dict for debugging.
    """
    if isinstance(ir_or_markdown, dict):
        body = ir_or_markdown.get("content_md") or ""
        fm = ir_or_markdown.get("frontmatter") or {}
    else:
        fm, body = _strip_frontmatter(ir_or_markdown)

    rationale: dict[str, float] = {}

    # 1. Frontmatter type bias
    page_type = (fm.get("type") or "").lower()
    type_score = _TYPE_BIAS.get(page_type, 0.05)  # unknown type = small default
    rationale["type_bias"] = type_score

    # 2. Step structure
    step_hits = _count_pattern_hits(_STEP_PATTERNS, body, multiline=True)
    has_steps = step_hits >= 2
    step_score = 0.20 if has_steps else (0.08 if step_hits == 1 else 0.0)
    rationale["steps"] = step_score

    # 3. Decision / branch language
    branch_hits = _count_pattern_hits(_BRANCH_PATTERNS, body)
    has_branches = branch_hits >= 1
    branch_score = min(0.15, 0.05 * branch_hits)
    rationale["branches"] = branch_score

    # 4. State machine vocabulary
    state_hits = _count_pattern_hits(_STATE_MACHINE_PATTERNS, body)
    has_state_machine = state_hits >= 1
    state_score = min(0.10, 0.05 * state_hits)
    rationale["state_machine"] = state_score

    # 5. Length
    char_count = len(body)
    if char_count >= 3000:
        len_score = 0.15
    elif char_count >= 1000:
        len_score = 0.10
    else:
        len_score = 0.0
    rationale["length"] = len_score
    has_outline_value = char_count >= 1500

    # 6. TOC potential — count H2 + H3 headings
    h2_count = len(re.findall(r"^##\s+\S", body, re.MULTILINE))
    h3_count = len(re.findall(r"^###\s+\S", body, re.MULTILINE))
    heading_count = h2_count + h3_count
    if heading_count >= 5:
        toc_score = 0.10
    elif heading_count >= 3:
        toc_score = 0.06
    else:
        toc_score = 0.0
    rationale["toc_potential"] = toc_score

    # 7. Visual cue density
    visual_hits = _count_pattern_hits(_VISUAL_CUE_PATTERNS, body)
    visual_score = min(0.10, 0.04 * visual_hits)
    rationale["visual_cues"] = visual_score

    audience_score = min(
        1.0,
        type_score + step_score + branch_score + state_score
        + len_score + toc_score + visual_score,
    )

    return ReaderProfile(
        audience_score=round(audience_score, 3),
        has_steps=has_steps,
        has_branches=has_branches,
        has_state_machine=has_state_machine,
        has_outline_value=has_outline_value,
        heading_count=heading_count,
        char_count=char_count,
        rationale=rationale,
    )
