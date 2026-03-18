"""Tests for LLM client utilities."""

import pytest

from orchestrator.llm_client import parse_json_response


class TestParseJsonResponse:
    def test_plain_json(self):
        """Plain JSON string should parse correctly."""
        text = '{"architecture_name": "Test", "nodes": []}'
        result = parse_json_response(text)
        assert result["architecture_name"] == "Test"

    def test_markdown_code_block(self):
        """JSON wrapped in ```json ... ``` should parse correctly."""
        text = '```json\n{"architecture_name": "Wrapped", "nodes": []}\n```'
        result = parse_json_response(text)
        assert result["architecture_name"] == "Wrapped"

    def test_markdown_code_block_no_lang(self):
        """JSON wrapped in ``` ... ``` (no language tag) should parse."""
        text = '```\n{"name": "test"}\n```'
        result = parse_json_response(text)
        assert result["name"] == "test"

    def test_invalid_json_raises(self):
        """Invalid JSON should raise ValueError."""
        with pytest.raises(ValueError, match="invalid JSON"):
            parse_json_response("this is not json")

    def test_empty_string_raises(self):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError):
            parse_json_response("")
