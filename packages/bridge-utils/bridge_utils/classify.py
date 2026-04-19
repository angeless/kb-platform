"""Path classification + tag suggestion (no LLM).

Given a markdown body, decide:
1. Which Hogwarts-KB sub-folder it should live in
   (wiki/concepts/ vs wiki/howtos/ vs wiki/analyses/ vs wiki/summaries/ vs wiki/entities/)
2. What tags to suggest in frontmatter
3. (Future) entity list

Strategy is lightweight — keyword + structural cues + YAKE keyphrases.
KeyBERT/spaCy NER are optional (loaded only if `bridge-utils[heavy]` installed).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

import yake

PageType = Literal["concept", "howto", "analysis", "summary", "entity", "lesson", "unknown"]


@dataclass
class TagSuggestion:
    """Output of the path/tag classifier."""

    page_type: PageType
    suggested_path: str  # e.g. "wiki/concepts/foo.md" — relative to KB root
    confidence: float    # 0.0 to 1.0
    tags: list[str] = field(default_factory=list)
    reasoning: list[str] = field(default_factory=list)


# Heuristic scoring: count keyword/phrase occurrences in text.
_HOWTO_HINTS = [
    r"\bhow to\b", r"\bsteps?:\b", r"\bguide:?\b",
    "如何", "步骤", "教程", "指南",
]
_ANALYSIS_HINTS = [
    r"\bcomparison\b", r"\bvs\b", r"\banalysis\b", r"\bdeep[- ]?dive\b",
    "对比", "分析", "深入", "调研",
]
_SUMMARY_HINTS = [
    r"\bsummary\b", r"\btl;?dr\b", r"\babstract\b", r"\bkey points?\b",
    "摘要", "概要", "要点", "总结",
]
_ENTITY_HINTS = [
    r"\bcompany\b", r"\bperson\b", r"\bproduct\b", r"\bteam\b",
    "公司", "团队", "产品", "工具",
]
_LESSON_HINTS = [
    r"\blesson\b", r"\blearned\b", r"\bmistake\b", r"\bpostmortem\b",
    "教训", "复盘", "经验", "踩坑",
]


def _count_hints(text: str, hints: list[str]) -> int:
    text_lower = text.lower()
    score = 0
    for h in hints:
        if h.startswith("\\b") or "\\" in h:
            # regex pattern
            score += len(re.findall(h, text_lower, flags=re.IGNORECASE))
        else:
            # plain CJK / multi-char string
            score += text_lower.count(h.lower())
    return score


def _has_h2_steps(text: str) -> bool:
    """Detect '## Step 1' / '## 第一步' patterns indicating a procedural doc."""
    return bool(re.search(r"^##\s+(?:step|第|step)\b.*\d", text, re.IGNORECASE | re.MULTILINE))


def _extract_tags(text: str, lang_hint: str = "auto", top_n: int = 5) -> list[str]:
    """Extract top-N keyphrases via YAKE."""
    # YAKE supports lang codes: 'en', 'zh' (with jieba), 'auto'
    extractor = yake.KeywordExtractor(
        lan="en" if lang_hint == "english" else "zh" if lang_hint == "chinese" else "en",
        n=2,  # up to bigrams
        top=top_n,
    )
    try:
        keywords = extractor.extract_keywords(text)
    except Exception:
        return []

    # YAKE returns (phrase, score). Lower score = more important.
    return [kw for kw, _ in sorted(keywords, key=lambda x: x[1])[:top_n]]


def _detect_language(text: str) -> str:
    cjk = sum(1 for ch in text[:2000] if "\u4e00" <= ch <= "\u9fff")
    return "chinese" if cjk > 50 else "english"


def classify_path(
    markdown_body: str,
    *,
    title_hint: str | None = None,
    existing_frontmatter_type: str | None = None,
) -> TagSuggestion:
    """Classify a markdown body to a Hogwarts-KB layer + suggest tags.

    Args:
        markdown_body: the markdown content (with or without frontmatter)
        title_hint: optional title to guide path naming
        existing_frontmatter_type: if frontmatter already has `type:`, honor it
    """
    # Honor explicit frontmatter type if present and valid
    if existing_frontmatter_type in {"concept", "howto", "analysis", "summary", "entity", "lesson"}:
        page_type = existing_frontmatter_type  # type: ignore[assignment]
        return TagSuggestion(
            page_type=page_type,
            suggested_path=f"wiki/{page_type}s/{_slugify(title_hint or 'untitled')}.md",
            confidence=1.0,
            tags=_extract_tags(markdown_body, _detect_language(markdown_body)),
            reasoning=["explicit frontmatter `type` field"],
        )

    text = markdown_body
    lang = _detect_language(text)

    scores = {
        "howto": _count_hints(text, _HOWTO_HINTS) + (3 if _has_h2_steps(text) else 0),
        "analysis": _count_hints(text, _ANALYSIS_HINTS),
        "summary": _count_hints(text, _SUMMARY_HINTS),
        "entity": _count_hints(text, _ENTITY_HINTS),
        "lesson": _count_hints(text, _LESSON_HINTS),
    }

    # Default to 'concept' (the most generic wiki page type)
    best_type: PageType
    best_score: int
    if max(scores.values()) == 0:
        best_type = "concept"
        best_score = 0
    else:
        best_type, best_score = max(scores.items(), key=lambda kv: kv[1])  # type: ignore[assignment]

    total = sum(scores.values()) or 1
    confidence = min(1.0, 0.3 + 0.7 * (best_score / total)) if best_score else 0.3

    # Map page_type → folder
    folder_map = {
        "concept": "wiki/concepts",
        "howto": "wiki/howtos",
        "analysis": "wiki/analyses",
        "summary": "wiki/summaries",
        "entity": "wiki/entities",
        "lesson": "lessons",
        "unknown": "wiki/concepts",
    }
    folder = folder_map[best_type]

    slug = _slugify(title_hint or "untitled")
    suggested = f"{folder}/{slug}.md"

    reasoning = [f"{k} score = {v}" for k, v in scores.items() if v > 0]
    if not reasoning:
        reasoning = ["no strong signals; defaulting to concept"]

    tags = _extract_tags(text, lang)

    return TagSuggestion(
        page_type=best_type,
        suggested_path=suggested,
        confidence=round(confidence, 2),
        tags=tags,
        reasoning=reasoning,
    )


def _slugify(s: str) -> str:
    """Convert a title to a safe filename slug."""
    s = s.strip().lower()
    s = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = s.strip("-")
    return s or "untitled"
