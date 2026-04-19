"""Mermaid diagram generator — derive a flowchart / state-diagram from
markdown structure.

Strategy:
  - has_steps           → flowchart TD with sequential nodes
  - has_state_machine   → stateDiagram-v2 with detected states
  - has_branches        → flowchart with diamond decision nodes
  - else                → None (no diagram)

Pure structural extraction; no LLM. The diagram is approximate (it
reflects the headings, not the prose semantics) but good enough as a
"40-second skim" view for a human reader.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MermaidDiagram:
    kind: str  # "flowchart" | "stateDiagram" | "decision-flowchart"
    code: str  # The full ```mermaid ... ``` block (no fences here)


_STEP_HEADING_RE = re.compile(
    r"^##\s+(?:Step\s*(\d+)[:\.\)]?|第([一二三四五六七八九十\d]+)步[:：]?)\s*(.+?)$",
    re.IGNORECASE | re.MULTILINE,
)


def _extract_steps(body: str) -> list[tuple[str, str]]:
    """Find '## Step N: title' or '## 第N步: title' headings.

    Returns list of (label, full_title). Empty list if none found.
    """
    out: list[tuple[str, str]] = []
    for m in _STEP_HEADING_RE.finditer(body):
        n = m.group(1) or m.group(2) or ""
        title = (m.group(3) or "").strip().rstrip(":：")
        if title:
            label = f"Step {n}: {title[:40]}" if n else title[:40]
            out.append((str(len(out)), label))
    return out


def _build_flowchart(steps: list[tuple[str, str]]) -> str:
    """Generate a mermaid flowchart TD from sequential steps."""
    lines = ["flowchart TD"]
    for i, (sid, label) in enumerate(steps):
        # Mermaid label: escape quotes
        safe_label = label.replace('"', "'")
        lines.append(f'    n{sid}["{safe_label}"]')
    for i in range(len(steps) - 1):
        lines.append(f"    n{steps[i][0]} --> n{steps[i+1][0]}")
    return "\n".join(lines)


def _extract_states(body: str) -> list[str]:
    """Find state-machine state names from text patterns like 'state X' or
    'X --> Y'.
    """
    states: set[str] = set()
    # Pattern: "X --> Y" or "X -> Y"
    for m in re.finditer(r"\b([A-Za-z][A-Za-z0-9_]+)\s*[-–—]+>\s*([A-Za-z][A-Za-z0-9_]+)\b", body):
        states.add(m.group(1))
        states.add(m.group(2))
    # Pattern: explicit "state X"
    for m in re.finditer(r"\bstate\s+([A-Za-z][A-Za-z0-9_]+)\b", body, re.IGNORECASE):
        states.add(m.group(1))
    return sorted(states)


def _build_state_diagram(body: str) -> str | None:
    states = _extract_states(body)
    if len(states) < 2:
        return None

    transitions: list[tuple[str, str]] = []
    for m in re.finditer(r"\b([A-Za-z][A-Za-z0-9_]+)\s*[-–—]+>\s*([A-Za-z][A-Za-z0-9_]+)\b", body):
        transitions.append((m.group(1), m.group(2)))
    if not transitions:
        return None

    lines = ["stateDiagram-v2"]
    seen_pairs: set[tuple[str, str]] = set()
    for a, b in transitions:
        if (a, b) in seen_pairs:
            continue
        seen_pairs.add((a, b))
        lines.append(f"    {a} --> {b}")
    # Mark the first state as initial
    first = transitions[0][0]
    lines.insert(1, f"    [*] --> {first}")
    return "\n".join(lines)


def generate_mermaid(profile, body: str) -> MermaidDiagram | None:
    """Pick the best diagram type for this content. May return None.

    Args:
        profile: ReaderProfile from bridge_visual.profile
        body:    markdown body (frontmatter stripped)

    Returns:
        MermaidDiagram or None
    """
    # Priority: state machine > steps > branches
    if profile.has_state_machine:
        sd = _build_state_diagram(body)
        if sd:
            return MermaidDiagram(kind="stateDiagram", code=sd)

    if profile.has_steps:
        steps = _extract_steps(body)
        if len(steps) >= 2:
            return MermaidDiagram(kind="flowchart", code=_build_flowchart(steps))

    # No structural cue strong enough → no diagram. Better to omit than fabricate.
    return None
