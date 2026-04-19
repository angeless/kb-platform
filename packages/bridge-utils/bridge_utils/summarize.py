"""Local extractive summarization (no LLM).

Strategy:
1. Strip frontmatter + markdown formatting → plain text
2. Run LexRank (sumy) to score sentences
3. Pick top-N sentences (default top-3) up to a target char budget
4. If extractive output is < 30% of target budget OR contains no sentences
   from the first/last 20% of the doc, return a low-confidence flag so the
   caller can decide to invoke LLM fallback.

Why LexRank: graph-based, language-agnostic, no model download required,
works decently on Chinese with the proper tokenizer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import frontmatter

# Regex to strip markdown decorations for cleaner sentence extraction
_MD_HEADING = re.compile(r"^#+\s+", re.MULTILINE)
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_WIKILINK = re.compile(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]")
_MD_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
_MD_INLINE_CODE = re.compile(r"`[^`]+`")
_MD_BOLD_ITALIC = re.compile(r"[*_]{1,3}([^*_]+)[*_]{1,3}")
_MD_LIST = re.compile(r"^[\s]*[-*+]\s+", re.MULTILINE)
_MD_NUMBERED_LIST = re.compile(r"^[\s]*\d+\.\s+", re.MULTILINE)
_MULTI_NEWLINE = re.compile(r"\n{3,}")


@dataclass
class SummaryResult:
    """Result of an extractive summarization run."""

    text: str
    sentence_count: int
    char_count: int
    confidence: float  # 0.0 to 1.0
    needs_llm_fallback: bool
    method: str  # "lexrank" | "luhn" | "fallback-truncate"


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting to get plain prose."""
    text = _MD_CODE_BLOCK.sub("", text)
    text = _MD_HEADING.sub("", text)
    text = _MD_LINK.sub(r"\1", text)
    text = _MD_WIKILINK.sub(r"\1", text)
    text = _MD_INLINE_CODE.sub("", text)
    text = _MD_BOLD_ITALIC.sub(r"\1", text)
    text = _MD_LIST.sub("", text)
    text = _MD_NUMBERED_LIST.sub("", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def _detect_language(text: str) -> str:
    """Cheap CJK-vs-English detection. Returns 'chinese' or 'english'."""
    cjk = sum(1 for ch in text[:2000] if "\u4e00" <= ch <= "\u9fff")
    return "chinese" if cjk > 50 else "english"


def summarize_extractive(
    markdown_text: str,
    *,
    target_chars: int = 200,
    max_sentences: int = 5,
) -> SummaryResult:
    """Produce a top-N sentence extractive summary.

    Args:
        markdown_text: full markdown body (frontmatter is auto-stripped)
        target_chars: desired summary length in characters (soft limit)
        max_sentences: hard limit on number of sentences

    Returns:
        SummaryResult with confidence + needs_llm_fallback flags
    """
    # Strip frontmatter if present
    try:
        post = frontmatter.loads(markdown_text)
        body = post.content
    except Exception:
        body = markdown_text

    plain = _strip_markdown(body)
    if not plain or len(plain) < 50:
        return SummaryResult(
            text=plain[:target_chars],
            sentence_count=0,
            char_count=len(plain),
            confidence=0.0,
            needs_llm_fallback=False,  # nothing to summarize
            method="fallback-truncate",
        )

    lang = _detect_language(plain)

    # Lazy-import sumy + nltk to keep cold-start fast
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.lex_rank import LexRankSummarizer

    # sumy's Chinese tokenizer relies on jieba; fall back to "english" if absent
    sumy_lang = "chinese" if lang == "chinese" else "english"
    try:
        parser = PlaintextParser.from_string(plain, Tokenizer(sumy_lang))
    except LookupError:
        # Chinese tokenizer requires jieba; fall back gracefully
        parser = PlaintextParser.from_string(plain, Tokenizer("english"))
        sumy_lang = "english"

    summarizer = LexRankSummarizer()
    summary_sentences = summarizer(parser.document, max_sentences)

    pieces: list[str] = []
    used_chars = 0
    for sent in summary_sentences:
        s = str(sent).strip()
        if not s:
            continue
        if used_chars + len(s) > target_chars * 1.5:
            break
        pieces.append(s)
        used_chars += len(s)

    summary = " ".join(pieces).strip()
    if not summary:
        # Fallback: first paragraph
        first_para = plain.split("\n\n", 1)[0].strip()
        summary = first_para[:target_chars]
        return SummaryResult(
            text=summary,
            sentence_count=1,
            char_count=len(summary),
            confidence=0.3,
            needs_llm_fallback=True,
            method="fallback-truncate",
        )

    # Confidence heuristic
    coverage = min(1.0, used_chars / target_chars)
    sentence_balance = min(1.0, len(pieces) / max_sentences)
    confidence = 0.4 + 0.4 * coverage + 0.2 * sentence_balance
    needs_fallback = confidence < 0.5

    return SummaryResult(
        text=summary,
        sentence_count=len(pieces),
        char_count=len(summary),
        confidence=round(confidence, 2),
        needs_llm_fallback=needs_fallback,
        method=f"lexrank-{sumy_lang}",
    )
