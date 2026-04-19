"""Top-level augmentation: profile → mermaid + outline → splice into markdown.

Idempotent splice contract:

    BEFORE first augmentation:
        ---
        frontmatter
        ---

        # Original H1
        body...

    AFTER augmentation (audience_score >= threshold):
        ---
        frontmatter
        ---

        <!-- bridge-visual:start v=1 audience=0.78 -->

        > 🤖 Auto-generated visual aids by KBSQL bridge.
        > Edit at the source spec; re-augment to refresh.

        ```mermaid
        flowchart TD
            ...
        ```

        <details>
        <summary>📖 Outline</summary>
        ...
        </details>

        <!-- bridge-visual:end -->

        # Original H1
        body...

Re-augmenting strips the previous block first (matched by the markers),
then re-injects. Original content untouched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import frontmatter

from .mermaid import MermaidDiagram, generate_mermaid
from .outline import generate_outline
from .profile import (
    AUDIENCE_HUMAN_THRESHOLD_DEFAULT,
    ReaderProfile,
    profile_reader,
)

# Marker comments — DO NOT change without updating the regex below.
BRIDGE_VISUAL_MARKERS = {
    "start_prefix": "<!-- bridge-visual:start",
    "end": "<!-- bridge-visual:end -->",
}

_BLOCK_RE = re.compile(
    r"<!--\s*bridge-visual:start[^>]*-->.*?<!--\s*bridge-visual:end\s*-->\s*\n?",
    re.DOTALL,
)


@dataclass
class AugmentResult:
    augmented: bool
    output: str
    profile: ReaderProfile
    mermaid: MermaidDiagram | None
    outline: str | None
    skipped_reason: str | None = None


def _build_block(
    profile: ReaderProfile,
    mermaid: MermaidDiagram | None,
    outline: str | None,
) -> str:
    parts = [
        f"<!-- bridge-visual:start v=1 audience={profile.audience_score} -->",
        "",
        "> 🤖 Auto-generated visual aids by KBSQL bridge.",
        "> Original content unchanged below. Re-run bridge_visual.augment to refresh.",
        "",
    ]
    if mermaid is not None:
        parts.append(f"```mermaid\n{mermaid.code}\n```")
        parts.append("")
    if outline is not None:
        parts.append(outline)
        parts.append("")
    parts.append(BRIDGE_VISUAL_MARKERS["end"])
    return "\n".join(parts)


def _strip_existing_block(body: str) -> str:
    """Remove any previous bridge-visual block. Idempotent."""
    return _BLOCK_RE.sub("", body)


def augment_markdown(
    markdown_text: str,
    *,
    threshold: float = AUDIENCE_HUMAN_THRESHOLD_DEFAULT,
) -> AugmentResult:
    """Read markdown, profile it, and (if human-leaning) splice in mermaid + outline.

    Args:
        markdown_text: full file content (frontmatter included)
        threshold: minimum audience_score to augment (default 0.6)

    Returns:
        AugmentResult — `augmented=False` when below threshold, with the
        original text returned unchanged.
    """
    try:
        post = frontmatter.loads(markdown_text)
        fm = dict(post.metadata)
        body = post.content or ""
    except Exception:
        fm = {}
        body = markdown_text

    # Strip any previous block before profiling so re-augmentation is stable.
    clean_body = _strip_existing_block(body)

    profile = profile_reader({"frontmatter": fm, "content_md": clean_body})
    mermaid = generate_mermaid(profile, clean_body)
    outline = (
        generate_outline(clean_body) if profile.has_outline_value else None
    )

    if profile.audience_score < threshold:
        # Below threshold: still write back the cleaned body (in case there
        # was a stale block from a previous run that no longer qualifies).
        out_post = frontmatter.Post(clean_body, **fm)
        return AugmentResult(
            augmented=False,
            output=frontmatter.dumps(out_post) + "\n",
            profile=profile,
            mermaid=mermaid,
            outline=outline,
            skipped_reason=(
                f"audience_score={profile.audience_score} < threshold={threshold}"
            ),
        )

    if mermaid is None and outline is None:
        return AugmentResult(
            augmented=False,
            output=frontmatter.dumps(frontmatter.Post(clean_body, **fm)) + "\n",
            profile=profile,
            mermaid=None,
            outline=None,
            skipped_reason="no diagram or outline could be generated",
        )

    block = _build_block(profile, mermaid, outline)
    new_body = block + "\n\n" + clean_body.lstrip("\n")
    out_post = frontmatter.Post(new_body, **fm)
    return AugmentResult(
        augmented=True,
        output=frontmatter.dumps(out_post) + "\n",
        profile=profile,
        mermaid=mermaid,
        outline=outline,
    )
