"""Image OCR parser — extracts text from images using Tesseract OCR.

Uses pytesseract (Tesseract wrapper) + Pillow for image loading.
Supports: PNG, JPG, JPEG, BMP, TIFF, WEBP.
Language: Chinese Simplified + English (chi_sim+eng).

Conforms to the parser interface: parse(content: bytes, filename: str) -> list[dict].
"""

import io
import logging

logger = logging.getLogger(__name__)

# Minimum characters to consider OCR output as meaningful
MIN_TEXT_LENGTH = 10

# Tesseract language config: Chinese Simplified + English
TESSERACT_LANG = "chi_sim+eng"


def parse(content: bytes, filename: str) -> list[dict]:
    """Parse an image file using OCR to extract text.

    Returns list of dicts with keys: content_text, page_or_timestamp, tags.
    Returns empty list if OCR is unavailable or image has no readable text.
    """
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError(
            "OCR 依赖缺失：Pillow 未安装，"
            "请在 ingestion-worker 容器中运行 pip install Pillow"
        )

    try:
        import pytesseract
    except ImportError:
        raise RuntimeError(
            "OCR 依赖缺失：pytesseract 未安装，"
            "请在 ingestion-worker 容器中运行 pip install pytesseract"
        )

    try:
        image = Image.open(io.BytesIO(content))
    except Exception as e:
        logger.error("Failed to open image %s: %s", filename, e)
        return []

    # Extract image metadata
    width, height = image.size
    img_format = image.format or "unknown"

    try:
        text = pytesseract.image_to_string(image, lang=TESSERACT_LANG)
    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "OCR 依赖缺失：系统未安装 Tesseract，"
            "请在容器中运行 apt-get install tesseract-ocr"
        )
    except Exception as e:
        logger.warning("OCR failed for %s: %s", filename, e)
        return []

    text = text.strip()

    if len(text) < MIN_TEXT_LENGTH:
        logger.info("OCR extracted too little text from %s (%d chars) — skipping", filename, len(text))
        return []

    # Split by double newline into paragraphs (same as text_parser)
    from .ir_utils import detect_language, infer_structure_type

    paragraphs = text.split("\n\n")
    chunks = []
    for i, para in enumerate(paragraphs):
        cleaned = para.strip()
        if not cleaned:
            continue
        chunks.append({
            "content_text": cleaned,
            "page_or_timestamp": f"ocr-region-{i + 1}",
            "tags": {
                "source_type": "image",
                "filename": filename,
                "ocr_lang": TESSERACT_LANG,
                "image_width": width,
                "image_height": height,
                "image_format": img_format,
            },
            "original_format": "ocr",
            "structure_type": infer_structure_type(cleaned),
            "extraction_confidence": 0.7,
            "language": detect_language(cleaned),
            "semantic_boundaries": None,
        })

    logger.info("OCR parsed %s (%s, %dx%d): %d chunks", filename, img_format, width, height, len(chunks))
    return chunks
