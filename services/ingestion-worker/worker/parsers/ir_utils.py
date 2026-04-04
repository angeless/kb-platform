"""IR (Intermediate Representation) utilities for parsers.

Simple helpers for populating IR fields without external NLP dependencies.
"""

import re


def detect_language(text: str) -> str:
    """Detect language using simple CJK character ratio.

    Returns "zh" if >50% CJK chars, "en" if <10%, "mixed" otherwise.
    """
    if not text:
        return "en"
    # Count CJK Unified Ideographs range
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    alpha_count = len(re.findall(r"[a-zA-Z]", text))
    total = cjk_count + alpha_count
    if total == 0:
        return "en"
    ratio = cjk_count / total
    if ratio > 0.5:
        return "zh"
    elif ratio < 0.1:
        return "en"
    return "mixed"


def infer_structure_type(text: str) -> str | None:
    """Infer structure type from text content heuristics.

    Returns "heading", "list", "table", "code", "paragraph", or None.
    """
    stripped = text.strip()
    if not stripped:
        return None
    # Heading: short line, no period at end
    if len(stripped) < 80 and not stripped.endswith((".", "。", "，", ",")):
        lines = stripped.split("\n")
        if len(lines) == 1:
            return "heading"
    # List: starts with bullet or number
    if re.match(r"^(\d+[\.\)、]|[-•*])\s", stripped):
        return "list"
    # Code: contains common code patterns
    if re.search(r"(def |class |import |function |const |var |let |\{|\}|=>|//)", stripped):
        return "code"
    return "paragraph"
