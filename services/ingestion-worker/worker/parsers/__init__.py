"""Parser registry — maps asset_type to parser module."""

from . import asr_parser, ocr_parser, pdf_parser, text_parser, video_parser, word_parser

# Maps asset_type -> parser module (must have parse(content: bytes, filename: str) -> list[dict])
PARSERS: dict[str, object] = {
    "text": text_parser,
    "pdf": pdf_parser,
    "docx": word_parser,
    # "doc" (legacy .doc) intentionally omitted — get_parser returns None → unsupported
    "image": ocr_parser,
    "audio": asr_parser,
    "video": video_parser,
}

# Asset types that have a registered parser
SUPPORTED_TYPES: set[str] = set(PARSERS.keys())


def get_parser(asset_type: str):
    """Get parser module for asset_type, or None if not supported."""
    return PARSERS.get(asset_type)


def is_parseable(asset_type: str) -> bool:
    """Check if an asset type has a registered parser."""
    return asset_type in SUPPORTED_TYPES
