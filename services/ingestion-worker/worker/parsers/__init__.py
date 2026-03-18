"""Parser registry — maps asset_type to parser module."""

from . import text_parser

# Maps asset_type -> parser module (must have parse(content: bytes, filename: str) -> list[dict])
PARSERS: dict[str, object] = {
    "text": text_parser,
}


def get_parser(asset_type: str):
    """Get parser module for asset_type, or None if not supported."""
    return PARSERS.get(asset_type)
