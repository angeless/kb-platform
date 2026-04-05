"""Word document parser — extracts text from .docx files using python-docx.

Parses paragraphs, groups by heading level, and merges body text under
its nearest heading. Conforms to parser interface:
parse(content: bytes, filename: str) -> list[dict].
"""

import io
import logging

logger = logging.getLogger(__name__)

# Maximum characters per chunk before splitting
MAX_CHUNK_CHARS = 3000


def parse(content: bytes, filename: str) -> list[dict]:
    """Parse a .docx file and return structured text chunks.

    Raises ValueError if the file is not a valid .docx.
    Returns empty list for documents with no text content.
    """
    try:
        import docx
    except ImportError:
        raise RuntimeError(
            "Word 解析依赖缺失：python-docx 未安装，"
            "请在 ingestion-worker 容器中运行 pip install python-docx"
        )

    try:
        doc = docx.Document(io.BytesIO(content))
    except Exception as e:
        raise ValueError(f"不是有效的 .docx 文件: {filename} ({e})")

    # Collect paragraphs with heading info
    sections: list[dict] = []
    current_heading: str | None = None
    current_level: int = 0
    current_texts: list[str] = []
    current_start: int = 1

    for i, para in enumerate(doc.paragraphs, start=1):
        text = para.text.strip()
        if not text:
            continue

        level = _heading_level(para.style.name)

        if level > 0:
            # Flush previous section
            if current_texts:
                sections.append({
                    "texts": current_texts,
                    "heading_text": current_heading,
                    "heading_level": current_level,
                    "start_para": current_start,
                })
            current_heading = text
            current_level = level
            current_texts = [text]
            current_start = i
        else:
            if not current_texts:
                current_start = i
            current_texts.append(text)

    # Flush last section
    if current_texts:
        sections.append({
            "texts": current_texts,
            "heading_text": current_heading,
            "heading_level": current_level,
            "start_para": current_start,
        })

    if not sections:
        logger.info("Word document %s has no text content", filename)
        return []

    # Build chunks, splitting oversized sections
    chunks: list[dict] = []
    for section in sections:
        merged = "\n\n".join(section["texts"])
        base_ts = f"para-{section['start_para']}"

        if len(merged) <= MAX_CHUNK_CHARS:
            chunks.append(_make_chunk(
                merged, base_ts, filename,
                section["heading_level"], section["heading_text"],
            ))
        else:
            parts = merged.split("\n\n")
            part_buf: list[str] = []
            part_idx = 1
            for part in parts:
                if part_buf and len("\n\n".join(part_buf)) + 2 + len(part) > MAX_CHUNK_CHARS:
                    chunks.append(_make_chunk(
                        "\n\n".join(part_buf),
                        f"{base_ts}-part-{part_idx}",
                        filename,
                        section["heading_level"], section["heading_text"],
                    ))
                    part_idx += 1
                    part_buf = []
                part_buf.append(part)
            if part_buf:
                chunks.append(_make_chunk(
                    "\n\n".join(part_buf),
                    f"{base_ts}-part-{part_idx}" if part_idx > 1 else base_ts,
                    filename,
                    section["heading_level"], section["heading_text"],
                ))

    logger.info("Word parsed %s: %d sections, %d chunks", filename, len(sections), len(chunks))
    return chunks


def _heading_level(style_name: str) -> int:
    """Extract heading level from style name. Returns 0 for non-headings."""
    if not style_name:
        return 0
    name = style_name.lower()
    if name == "heading 1":
        return 1
    if name == "heading 2":
        return 2
    if name == "heading 3":
        return 3
    return 0


def _make_chunk(
    text: str,
    timestamp: str,
    filename: str,
    heading_level: int,
    heading_text: str | None,
) -> dict:
    from .ir_utils import detect_language, infer_structure_type

    return {
        "content_text": text,
        "page_or_timestamp": timestamp,
        "tags": {
            "source_type": "docx",
            "filename": filename,
            "heading_level": heading_level,
            "heading_text": heading_text,
        },
        "original_format": "docx",
        "structure_type": "heading" if heading_level > 0 else infer_structure_type(text),
        "extraction_confidence": 1.0,
        "language": detect_language(text),
        "semantic_boundaries": None,
    }
