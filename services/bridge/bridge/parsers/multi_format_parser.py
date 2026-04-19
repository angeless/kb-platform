"""Multi-format parser — converts office/csv/web/etc. to markdown.

Strategy (LLM-minimizing):
- Office docs (docx/pptx/xlsx/csv/html/epub): markitdown 0.1.5 (no LLM)
- PDFs (text + scanned), images (OCR): docling — lazy-loaded ONLY when invoked
- Web URLs: trafilatura — fully local

The parser dispatches by file extension. Unknown formats raise
UnsupportedFormatException so the caller can fall back to raw bytes
+ best-effort markdown wrap.

This parser is INDEPENDENT from services/ingestion-worker/worker/parsers/.
The ingestion-worker has its own pdf_parser/word_parser/asr_parser/etc. for
the existing 9-stage pipeline. The bridge multi_format_parser is for KB-side
sync — when a user drops a non-markdown file into the KB filesystem, this
parser converts it to markdown so the KB stays markdown-native.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Extensions handled by markitdown (verified against 0.1.5 in our env).
_MARKITDOWN_EXTS = {
    ".docx", ".pptx", ".xlsx", ".xls",
    ".csv", ".tsv",
    ".html", ".htm",
    ".epub",
    ".pdf",  # markitdown's PDF is plain-text only — for layout use docling
    ".zip",  # zip of supported formats
    ".json", ".xml",
}

# Extensions where docling beats markitdown (layout-aware).
_DOCLING_PREFER_EXTS = {
    ".pdf",  # for structure
    ".png", ".jpg", ".jpeg", ".tiff", ".bmp",  # image OCR
}


class UnsupportedFormat(ValueError):
    """Raised when no installed parser handles this file extension."""


def _markitdown_convert(path: Path) -> tuple[str, str | None]:
    """Run markitdown without LLM. Returns (markdown_text, optional_title)."""
    from markitdown import MarkItDown  # lazy import (heavy)

    md = MarkItDown(enable_builtins=True, enable_plugins=False)
    result = md.convert(str(path))
    text = (result.text_content or "").strip() + "\n"
    title = getattr(result, "title", None)
    return text, title


def _docling_convert(path: Path) -> tuple[str, str | None]:
    """Run docling for layout-aware conversion. Returns (markdown_text, optional_title)."""
    try:
        from docling.document_converter import DocumentConverter  # lazy import (very heavy)
    except ImportError as e:
        raise UnsupportedFormat(
            f"docling not installed; cannot convert {path.suffix}. "
            "Install with: pip install docling"
        ) from e

    converter = DocumentConverter()
    result = converter.convert(str(path))
    md = result.document.export_to_markdown()
    return md.strip() + "\n", None


def _trafilatura_convert(url_or_html: str) -> tuple[str, str | None]:
    """Convert a URL or raw HTML to markdown via trafilatura."""
    try:
        import trafilatura  # lazy import
    except ImportError as e:
        raise UnsupportedFormat(
            "trafilatura not installed; cannot convert URLs. "
            "Install with: pip install trafilatura"
        ) from e

    if url_or_html.startswith(("http://", "https://")):
        downloaded = trafilatura.fetch_url(url_or_html)
        if downloaded is None:
            raise ValueError(f"Failed to fetch URL: {url_or_html}")
        html = downloaded
    else:
        html = url_or_html

    md = trafilatura.extract(html, output_format="markdown") or ""
    title = None
    metadata = trafilatura.extract_metadata(html)
    if metadata is not None:
        title = metadata.title or None
    return md.strip() + "\n", title


def parse_file(path: str | Path, *, prefer_docling_for_pdf: bool = True) -> dict[str, Any]:
    """Parse any supported file into the canonical bridge IR.

    Args:
        path: file path
        prefer_docling_for_pdf: if True (default), uses docling for PDFs (better
            layout). If False or docling not installed, falls back to markitdown.

    Returns:
        IR dict (same schema as bridge.parsers.markdown_parser.parse_markdown)

    Raises:
        UnsupportedFormat: extension not handled
        FileNotFoundError: path missing
    """
    p = Path(path).resolve()
    if not p.is_file():
        raise FileNotFoundError(f"Not a file: {p}")

    ext = p.suffix.lower()
    raw_size = p.stat().st_size

    title: str | None = None
    if ext == ".pdf" and prefer_docling_for_pdf:
        try:
            content_md, title = _docling_convert(p)
        except UnsupportedFormat:
            logger.info("docling unavailable; falling back to markitdown for %s", p.name)
            content_md, title = _markitdown_convert(p)
    elif ext in _DOCLING_PREFER_EXTS - {".pdf"}:
        # Image OCR — try docling, fall back to markitdown
        try:
            content_md, title = _docling_convert(p)
        except UnsupportedFormat:
            content_md, title = _markitdown_convert(p)
    elif ext in _MARKITDOWN_EXTS:
        content_md, title = _markitdown_convert(p)
    else:
        raise UnsupportedFormat(
            f"No parser handles extension {ext!r}. "
            f"Supported: {sorted(_MARKITDOWN_EXTS | _DOCLING_PREFER_EXTS)}"
        )

    final_title = title or p.stem

    return {
        "kind": "multi_format",
        "title": final_title,
        "content_md": content_md,
        "frontmatter": {},  # multi-format files have no frontmatter (yet)
        "wiki_links": [],   # converted markdown won't contain Obsidian links
        "outbound_urls": [],  # caller can post-process if needed
        "raw_size": raw_size,
        "content_hash": hashlib.sha256(content_md.encode("utf-8")).hexdigest(),
        "source_path": str(p),
        "source_format": ext.lstrip("."),
    }


def parse_url(url: str) -> dict[str, Any]:
    """Convert a web URL to the canonical bridge IR via trafilatura."""
    content_md, title = _trafilatura_convert(url)
    return {
        "kind": "web",
        "title": title or url,
        "content_md": content_md,
        "frontmatter": {"source": url},
        "wiki_links": [],
        "outbound_urls": [url],
        "raw_size": len(content_md.encode("utf-8")),
        "content_hash": hashlib.sha256(content_md.encode("utf-8")).hexdigest(),
        "source_path": url,
        "source_format": "web",
    }


def supported_extensions() -> set[str]:
    """Return the set of extensions parse_file() can handle."""
    return _MARKITDOWN_EXTS | _DOCLING_PREFER_EXTS
