"""PDF parser — extracts text from PDF files page by page.

Uses pymupdf (fitz) for text extraction. Each page becomes one chunk,
with page_or_timestamp recording the page number. Pages with long text
(>5000 chars) are split into sub-chunks by paragraph.

Conforms to the parser interface: parse(content: bytes, filename: str) -> list[dict].
"""

import io
import logging

import fitz  # pymupdf

logger = logging.getLogger(__name__)

MAX_CHUNK_CHARS = 5000


def parse(content: bytes, filename: str) -> list[dict]:
    """Parse a PDF file into chunks, one per page.

    Returns list of dicts with keys: content_text, page_or_timestamp, tags.
    Empty pages are skipped.
    """
    doc = fitz.open(stream=content, filetype="pdf")
    chunks = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()

        if not text:
            continue

        if len(text) <= MAX_CHUNK_CHARS:
            chunks.append({
                "content_text": text,
                "page_or_timestamp": f"page-{page_num + 1}",
                "tags": {"source_type": "pdf", "filename": filename, "page": page_num + 1},
            })
        else:
            # Split long pages by paragraph
            paragraphs = text.split("\n\n")
            sub_idx = 0
            for para in paragraphs:
                cleaned = para.strip()
                if not cleaned:
                    continue
                sub_idx += 1
                chunks.append({
                    "content_text": cleaned,
                    "page_or_timestamp": f"page-{page_num + 1}-part-{sub_idx}",
                    "tags": {"source_type": "pdf", "filename": filename, "page": page_num + 1},
                })

    page_count = len(doc)
    doc.close()
    logger.info("Parsed PDF %s: %d pages, %d chunks", filename, page_count, len(chunks))
    return chunks
