"""Unit tests for parsers."""

import fitz

from worker.parsers.text_parser import parse
from worker.parsers.pdf_parser import parse as pdf_parse


def _make_pdf(pages: list[str]) -> bytes:
    """Create a minimal PDF with the given page texts."""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestTextParser:
    def test_split_paragraphs(self):
        """Multiple paragraphs separated by blank lines should produce multiple chunks."""
        content = b"First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = parse(content, "test.txt")
        assert len(result) == 3
        assert result[0]["content_text"] == "First paragraph."
        assert result[1]["content_text"] == "Second paragraph."
        assert result[2]["content_text"] == "Third paragraph."
        assert result[0]["page_or_timestamp"] == "paragraph-1"

    def test_empty_content(self):
        """Empty file should return empty list."""
        result = parse(b"", "empty.txt")
        assert result == []

    def test_whitespace_only(self):
        """Whitespace-only content should return empty list."""
        result = parse(b"   \n\n   \n", "spaces.txt")
        assert result == []

    def test_single_paragraph(self):
        """Single paragraph without blank lines should produce 1 chunk."""
        content = b"This is a single paragraph\nwith line breaks\nbut no blank lines."
        result = parse(content, "single.txt")
        assert len(result) == 1
        assert "single paragraph" in result[0]["content_text"]

    def test_tags_contain_filename(self):
        """Each chunk should have tags with source_type and filename."""
        content = b"Some content."
        result = parse(content, "my_file.txt")
        assert len(result) == 1
        assert result[0]["tags"]["filename"] == "my_file.txt"
        assert result[0]["tags"]["source_type"] == "text"

    def test_skips_empty_paragraphs(self):
        """Empty paragraphs between content should be skipped."""
        content = b"First.\n\n\n\n\n\nSecond."
        result = parse(content, "gaps.txt")
        assert len(result) == 2


class TestPdfParser:
    def test_multi_page_pdf(self):
        """Multi-page PDF should produce one chunk per page."""
        pdf_bytes = _make_pdf(["Page one content", "Page two content", "Page three content"])
        result = pdf_parse(pdf_bytes, "test.pdf")
        assert len(result) == 3
        assert "Page one" in result[0]["content_text"]
        assert result[0]["page_or_timestamp"] == "page-1"
        assert result[1]["page_or_timestamp"] == "page-2"
        assert result[2]["page_or_timestamp"] == "page-3"

    def test_empty_pages_skipped(self):
        """Pages with no text should be skipped."""
        pdf_bytes = _make_pdf(["Has text", "", "Also has text"])
        result = pdf_parse(pdf_bytes, "gaps.pdf")
        assert len(result) == 2
        assert result[0]["page_or_timestamp"] == "page-1"
        assert result[1]["page_or_timestamp"] == "page-3"

    def test_single_page_pdf(self):
        """Single-page PDF should produce one chunk."""
        pdf_bytes = _make_pdf(["Hello world"])
        result = pdf_parse(pdf_bytes, "single.pdf")
        assert len(result) == 1
        assert "Hello" in result[0]["content_text"]

    def test_tags_contain_pdf_metadata(self):
        """Chunks should have correct tags."""
        pdf_bytes = _make_pdf(["Test content"])
        result = pdf_parse(pdf_bytes, "report.pdf")
        assert result[0]["tags"]["source_type"] == "pdf"
        assert result[0]["tags"]["filename"] == "report.pdf"
        assert result[0]["tags"]["page"] == 1

    def test_parser_registry(self):
        """PDF parser should be registered for 'pdf' and 'document' types."""
        from worker.parsers import get_parser
        assert get_parser("pdf") is not None
        assert get_parser("document") is not None
        assert get_parser("unknown_type") is None
