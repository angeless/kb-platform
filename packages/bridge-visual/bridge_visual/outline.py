"""Outline generator — produce a collapsible Markdown TOC from H1/H2/H3.

Output format (Obsidian + GitHub friendly):

    <details>
    <summary>📖 Outline</summary>

    - [Heading 1](#heading-1)
      - [Subheading](#subheading)
        - [Sub-sub](#sub-sub)

    </details>

GitHub anchor slug rules:
  - Lowercase
  - Spaces → hyphens
  - Strip everything except alphanumeric, hyphen, CJK
  - Multiple hyphens collapsed to one
"""

from __future__ import annotations

import re
import unicodedata


def _slug(heading: str) -> str:
    """Convert a heading to a GitHub-style anchor slug."""
    s = heading.strip().lower()
    s = unicodedata.normalize("NFKC", s)
    # Strip emojis and punctuation but keep CJK
    s = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-") or "heading"


def generate_outline(
    body: str,
    *,
    min_headings: int = 3,
    max_depth: int = 3,
) -> str | None:
    """Build a collapsible outline from headings in `body`.

    Returns None if there aren't enough headings to be useful.

    Args:
        body: markdown body (frontmatter already stripped)
        min_headings: skip outline if fewer than this many headings
        max_depth: include H1..H{max_depth} only

    Returns:
        Markdown HTML <details> block, or None.
    """
    headings: list[tuple[int, str]] = []
    for line in body.splitlines():
        m = re.match(r"^(#{1," + str(max_depth) + r"})\s+(.+?)\s*$", line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            if text:
                headings.append((level, text))

    if len(headings) < min_headings:
        return None

    # Build nested bullet list
    lines = ["<details>", "<summary>📖 Outline</summary>", ""]
    # Find the smallest level used to normalize indentation
    min_level = min(h[0] for h in headings)
    for level, text in headings:
        indent = "  " * (level - min_level)
        lines.append(f"{indent}- [{text}](#{_slug(text)})")
    lines.extend(["", "</details>"])
    return "\n".join(lines)
