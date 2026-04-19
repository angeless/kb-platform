"""Tests for bridge.parsers.multi_format_parser.

These cover the formats markitdown handles natively without LLM calls.
docling-dependent paths (PDF layout, image OCR) are mocked because docling
is a heavy install we defer to E2E phase.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bridge.parsers.multi_format_parser import (
    UnsupportedFormat,
    parse_file,
    supported_extensions,
)


def test_csv_to_markdown(tmp_path: Path) -> None:
    f = tmp_path / "data.csv"
    f.write_text("name,age,city\nAlice,30,Boston\nBob,25,NYC\n", encoding="utf-8")
    ir = parse_file(f)
    assert ir["kind"] == "multi_format"
    assert ir["source_format"] == "csv"
    assert "| name | age | city |" in ir["content_md"]
    assert "| Alice | 30 | Boston |" in ir["content_md"]
    assert ir["title"] == "data"  # filename stem (no markitdown-extracted title for CSV)
    assert ir["raw_size"] > 0
    assert len(ir["content_hash"]) == 64


def test_html_to_markdown(tmp_path: Path) -> None:
    f = tmp_path / "page.html"
    f.write_text(
        "<html><head><title>Test Page</title></head>"
        "<body><h1>Hello</h1><p>World <a href='https://example.com'>link</a></p></body></html>",
        encoding="utf-8",
    )
    ir = parse_file(f)
    assert ir["source_format"] == "html"
    assert "Hello" in ir["content_md"]


def test_unsupported_extension_raises(tmp_path: Path) -> None:
    f = tmp_path / "weird.xyz"
    f.write_text("hello", encoding="utf-8")
    with pytest.raises(UnsupportedFormat, match="No parser handles"):
        parse_file(f)


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_file(tmp_path / "nope.csv")


def test_supported_extensions_includes_office(tmp_path: Path) -> None:
    exts = supported_extensions()
    assert ".docx" in exts
    assert ".xlsx" in exts
    assert ".pptx" in exts
    assert ".csv" in exts
    assert ".pdf" in exts
    assert ".html" in exts


def test_pdf_falls_back_to_markitdown_when_docling_missing(tmp_path: Path, monkeypatch) -> None:
    """When docling is not installed, PDF parsing falls back to markitdown."""
    f = tmp_path / "tiny.pdf"
    # A minimal valid PDF (header + EOF)
    f.write_bytes(
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
        b"xref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000054 00000 n\n"
        b"trailer<</Size 3/Root 1 0 R>>\nstartxref\n100\n%%EOF\n"
    )
    # Force docling to fail by patching the import inside _docling_convert
    from bridge.parsers import multi_format_parser as mfp

    def _fake_docling(*args, **kwargs):
        raise UnsupportedFormat("docling not installed (test stub)")

    monkeypatch.setattr(mfp, "_docling_convert", _fake_docling)
    # markitdown will at least not crash on a valid (empty) PDF
    ir = parse_file(f)
    assert ir["source_format"] == "pdf"
    assert ir["kind"] == "multi_format"
    # content may be empty for a no-pages PDF, but the call must succeed
    assert isinstance(ir["content_md"], str)


def test_content_hash_deterministic(tmp_path: Path) -> None:
    f1 = tmp_path / "a.csv"
    f1.write_text("x,y\n1,2\n", encoding="utf-8")
    f2 = tmp_path / "b.csv"
    f2.write_text("x,y\n1,2\n", encoding="utf-8")
    assert parse_file(f1)["content_hash"] == parse_file(f2)["content_hash"]
