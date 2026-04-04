"""Web article content extraction using trafilatura.

Extracts clean article text, title, author, and date from raw HTML,
stripping navigation, ads, scripts, and other boilerplate.
"""

import html
import logging
import re

logger = logging.getLogger(__name__)


def extract_article(raw_html: str, url: str = "") -> dict:
    """Extract article content from HTML.

    Args:
        raw_html: Raw HTML string.
        url: Original URL (used by trafilatura for metadata heuristics).

    Returns:
        {"title": str, "body": str, "author": str | None, "date": str | None}
        - body is always plain text (never HTML)
        - On extraction failure, falls back to simple HTML tag stripping
    """
    empty_result = {"title": "", "body": "", "author": None, "date": None}

    if not raw_html or not raw_html.strip():
        return empty_result

    # If input has no HTML tags, return as-is
    if not _looks_like_html(raw_html):
        return {"title": "", "body": raw_html.strip(), "author": None, "date": None}

    # Try trafilatura extraction
    try:
        from trafilatura import bare_extraction

        doc = bare_extraction(raw_html, url=url or None, include_comments=False)
        if doc is not None and doc.text:
            return {
                "title": doc.title or "",
                "body": doc.text,
                "author": doc.author or None,
                "date": doc.date or None,
            }
    except Exception:
        logger.warning("trafilatura extraction failed for %s, falling back to tag stripping", url)

    # Fallback: simple HTML tag stripping
    body = _strip_html_tags(raw_html)
    return {"title": "", "body": body, "author": None, "date": None}


def _looks_like_html(text: str) -> bool:
    """Check if text contains HTML tags."""
    return bool(re.search(r"<[a-zA-Z][^>]*>", text))


def _strip_html_tags(raw_html: str) -> str:
    """Remove HTML tags and decode entities. Simple fallback when trafilatura fails."""
    # Remove script and style blocks entirely
    cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
    # Remove all remaining tags
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    # Decode HTML entities
    cleaned = html.unescape(cleaned)
    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
