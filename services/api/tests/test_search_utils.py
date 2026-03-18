"""Unit tests for search utility functions."""

from app.services.search_service import _extract_snippet


class TestExtractSnippet:
    def test_match_in_middle(self):
        text = "A" * 200 + "关键词" + "B" * 200
        snippet = _extract_snippet(text, "关键词", context=50)
        assert "关键词" in snippet
        assert snippet.startswith("...")
        assert snippet.endswith("...")

    def test_match_at_start(self):
        text = "关键词在开头后面还有很多内容" + "X" * 200
        snippet = _extract_snippet(text, "关键词", context=50)
        assert "关键词" in snippet
        assert not snippet.startswith("...")  # No ellipsis at start

    def test_match_at_end(self):
        text = "X" * 200 + "末尾关键词"
        snippet = _extract_snippet(text, "末尾关键词", context=50)
        assert "末尾关键词" in snippet
        assert not snippet.endswith("...")  # No ellipsis at end

    def test_no_match_returns_beginning(self):
        text = "这是一段没有匹配的文本"
        snippet = _extract_snippet(text, "不存在", context=50)
        assert snippet.startswith("这是")

    def test_case_insensitive(self):
        text = "Hello World this is a Test"
        snippet = _extract_snippet(text, "hello", context=20)
        assert "Hello" in snippet

    def test_short_text(self):
        text = "短文本"
        snippet = _extract_snippet(text, "短", context=100)
        assert "短文本" in snippet
