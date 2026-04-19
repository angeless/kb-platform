"""bridge-visual — reader-aware visual augmentation for KBSQL bridge.

Detects whether a markdown article is "human-leaning" (showcase, system,
how-to with steps) versus "AI-leaning" (raw data dump, dense reference)
and, when human-leaning, automatically appends:
  - A Mermaid flowchart / state-diagram / decision tree (when structure permits)
  - A collapsible outline (TOC) view

Insertion contract:
  - Output is the original markdown with a `<!-- bridge-visual:start -->` ...
    `<!-- bridge-visual:end -->` block injected immediately after the
    frontmatter and before the first H1.
  - Re-augmenting an already-augmented file is idempotent: the existing
    block is replaced.
  - The original author-written content is never modified outside the
    marker block.

Zero LLM calls in the default path. Optional GLM-4 polish for mermaid
diagram labels can be enabled via BRIDGE_VISUAL_LLM_POLISH=true (uses
the bridge LLM strict-mode router — never falls back to OpenAI).
"""

from .profile import (
    ReaderProfile,
    profile_reader,
    AUDIENCE_HUMAN_THRESHOLD_DEFAULT,
)
from .mermaid import generate_mermaid, MermaidDiagram
from .outline import generate_outline
from .augment import augment_markdown, AugmentResult, BRIDGE_VISUAL_MARKERS

__version__ = "0.1.0"
__all__ = [
    "profile_reader",
    "ReaderProfile",
    "AUDIENCE_HUMAN_THRESHOLD_DEFAULT",
    "generate_mermaid",
    "MermaidDiagram",
    "generate_outline",
    "augment_markdown",
    "AugmentResult",
    "BRIDGE_VISUAL_MARKERS",
]
