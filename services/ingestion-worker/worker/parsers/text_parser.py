"""Text file parser — splits text content into chunks by paragraph.

Each chunk is a paragraph (separated by double newlines).
Conforms to the parser interface: parse(content: bytes, filename: str) -> list[dict].
"""

import logging

logger = logging.getLogger(__name__)


def parse(content: bytes, filename: str) -> list[dict]:
    """Parse a text file into chunks by splitting on blank lines.

    Returns list of dicts with keys: content_text, page_or_timestamp, tags.
    Empty paragraphs are skipped.
    """
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    if not text.strip():
        return []

    # Split on double newlines (blank line = paragraph boundary)
    paragraphs = text.split("\n\n")
    chunks = []
    for i, para in enumerate(paragraphs):
        cleaned = para.strip()
        if not cleaned:
            continue
        chunks.append({
            "content_text": cleaned,
            "page_or_timestamp": f"paragraph-{i + 1}",
            "tags": {"source_type": "text", "filename": filename},
        })

    logger.info("Parsed %s into %d chunks", filename, len(chunks))
    return chunks
