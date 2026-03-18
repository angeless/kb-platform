"""Unit tests for parsers."""

from worker.parsers.text_parser import parse


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
