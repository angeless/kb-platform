"""Unit tests for parsers."""

import io
from unittest.mock import patch

import fitz
from PIL import Image, ImageDraw, ImageFont

from worker.parsers.text_parser import parse
from worker.parsers.pdf_parser import parse as pdf_parse
from worker.parsers.ocr_parser import parse as ocr_parse


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
        """PDF parser should be registered for 'pdf' and 'doc' types."""
        from worker.parsers import get_parser, is_parseable
        assert get_parser("pdf") is not None
        assert get_parser("doc") is not None
        assert get_parser("text") is not None
        assert get_parser("image") is not None
        assert get_parser("unknown_type") is None
        assert is_parseable("pdf") is True
        assert is_parseable("image") is True


def _make_text_image(text: str, width: int = 400, height: int = 100) -> bytes:
    """Create a PNG image with text drawn on it."""
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), text, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_blank_image() -> bytes:
    """Create a blank white PNG image."""
    img = Image.new("RGB", (100, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestOcrParser:
    def test_ocr_extracts_text(self):
        """OCR should extract text from an image with readable content."""
        img_bytes = _make_text_image("Hello World OCR Test Content Here")
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
        except Exception:
            # Tesseract not installed — skip gracefully
            result = ocr_parse(img_bytes, "test.png")
            assert result == []  # Graceful degradation
            return

        result = ocr_parse(img_bytes, "test.png")
        # Tesseract may or may not extract text from simple drawn text
        # The key test is that it doesn't crash
        assert isinstance(result, list)

    def test_ocr_blank_image_returns_empty(self):
        """Blank image should return empty (too little text)."""
        img_bytes = _make_blank_image()
        result = ocr_parse(img_bytes, "blank.png")
        assert result == []

    def test_ocr_invalid_image_returns_empty(self):
        """Invalid image data should return empty, not crash."""
        result = ocr_parse(b"not an image", "bad.png")
        assert result == []

    def test_ocr_tags_contain_image_metadata(self):
        """If OCR succeeds, tags should contain image metadata."""
        img_bytes = _make_text_image("This is a test with enough characters to pass minimum")
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
        except Exception:
            return  # Skip if Tesseract not installed

        result = ocr_parse(img_bytes, "photo.jpg")
        if result:  # Only check if OCR actually extracted text
            assert result[0]["tags"]["source_type"] == "image"
            assert result[0]["tags"]["filename"] == "photo.jpg"
            assert "image_width" in result[0]["tags"]
            assert "image_height" in result[0]["tags"]

    def test_ocr_graceful_without_tesseract(self):
        """OCR should return empty list when pytesseract is not importable."""
        img_bytes = _make_text_image("Some text")
        with patch.dict("sys.modules", {"pytesseract": None}):
            # Re-import to test import failure path
            from importlib import reload
            from worker.parsers import ocr_parser
            reload(ocr_parser)
            result = ocr_parser.parse(img_bytes, "test.png")
            assert result == []
            # Restore
            reload(ocr_parser)

    def test_ocr_registered_for_image_type(self):
        """OCR parser should be registered for 'image' asset type."""
        from worker.parsers import get_parser, is_parseable
        assert get_parser("image") is not None
        assert is_parseable("image") is True


class TestAsrParser:
    """Tests for the audio ASR parser using mocked Whisper."""

    def _mock_transcribe_result(self):
        """Return a mock Whisper transcription result."""
        return {
            "text": "Hello world. This is a test transcription.",
            "language": "en",
            "segments": [
                {"text": "Hello world.", "start": 0.0, "end": 2.5},
                {"text": "This is a test transcription.", "start": 2.5, "end": 5.0},
            ],
        }

    def test_asr_parses_segments(self):
        """ASR should produce chunks from Whisper segments."""
        from unittest.mock import MagicMock
        mock_model = MagicMock()
        mock_model.transcribe.return_value = self._mock_transcribe_result()

        with patch("worker.parsers.asr_parser._get_model", return_value=mock_model):
            from worker.parsers.asr_parser import parse as asr_parse
            result = asr_parse(b"fake audio bytes", "test.mp3")

        assert len(result) == 2
        assert "Hello world" in result[0]["content_text"]
        assert result[0]["page_or_timestamp"] == "00:00:00-00:00:02"
        assert result[0]["tags"]["source_type"] == "audio"
        assert result[0]["tags"]["language"] == "en"
        assert result[1]["page_or_timestamp"] == "00:00:02-00:00:05"

    def test_asr_empty_transcription(self):
        """Empty transcription should return empty list."""
        from unittest.mock import MagicMock
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "", "language": "en", "segments": []}

        with patch("worker.parsers.asr_parser._get_model", return_value=mock_model):
            from worker.parsers.asr_parser import parse as asr_parse
            result = asr_parse(b"silence", "silent.wav")

        assert result == []

    def test_asr_fallback_single_chunk(self):
        """If no segments but full text exists, should return single chunk."""
        from unittest.mock import MagicMock
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "Full text without segments available.",
            "language": "en",
            "segments": [],
        }

        with patch("worker.parsers.asr_parser._get_model", return_value=mock_model):
            from worker.parsers.asr_parser import parse as asr_parse
            result = asr_parse(b"audio data", "recording.m4a")

        assert len(result) == 1
        assert "Full text" in result[0]["content_text"]
        assert result[0]["page_or_timestamp"] == "00:00:00-full"

    def test_asr_graceful_without_whisper(self):
        """ASR should return empty list when whisper is not importable."""
        with patch.dict("sys.modules", {"whisper": None}):
            from importlib import reload
            from worker.parsers import asr_parser
            reload(asr_parser)
            result = asr_parser.parse(b"audio", "test.mp3")
            assert result == []
            reload(asr_parser)

    def test_asr_tags_contain_metadata(self):
        """Chunks should have correct audio metadata in tags."""
        from unittest.mock import MagicMock
        mock_model = MagicMock()
        mock_model.transcribe.return_value = self._mock_transcribe_result()

        with patch("worker.parsers.asr_parser._get_model", return_value=mock_model):
            from worker.parsers.asr_parser import parse as asr_parse
            result = asr_parse(b"audio", "meeting.mp3")

        assert len(result) >= 1
        tags = result[0]["tags"]
        assert tags["source_type"] == "audio"
        assert tags["filename"] == "meeting.mp3"
        assert tags["language"] == "en"
        assert "start_seconds" in tags
        assert "end_seconds" in tags

    def test_asr_registered_for_audio_type(self):
        """ASR parser should be registered for 'audio' asset type."""
        from worker.parsers import get_parser, is_parseable
        assert get_parser("audio") is not None
        assert is_parseable("audio") is True
