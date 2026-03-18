"""Parser registry — maps asset_type to parser module."""

from . import pdf_parser, text_parser

# Maps asset_type -> parser module (must have parse(content: bytes, filename: str) -> list[dict])
PARSERS: dict[str, object] = {
    "text": text_parser,
    "pdf": pdf_parser,
    "document": pdf_parser,  # .doc/.docx files also go through PDF pipeline for now
}


def get_parser(asset_type: str):
    """Get parser module for asset_type, or None if not supported."""
    return PARSERS.get(asset_type)
