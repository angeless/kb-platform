"""Unit tests for search utility functions."""

from app.services.search_service import _build_tsquery, _extract_snippet, _sanitize_tsquery_input


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


class TestSanitizeTsqueryInput:
    """Tests for tsquery input sanitization (T-36-02)."""

    def test_ampersand_removed(self):
        assert _sanitize_tsquery_input("hello&world") == "hello world"

    def test_parenthesis_removed(self):
        assert _sanitize_tsquery_input("hello(world") == "hello world"

    def test_pipe_removed(self):
        assert _sanitize_tsquery_input("a|b") == "a b"

    def test_exclamation_removed(self):
        assert _sanitize_tsquery_input("!hello") == "hello"

    def test_colon_removed(self):
        assert _sanitize_tsquery_input("field:value") == "field value"

    def test_asterisk_removed(self):
        assert _sanitize_tsquery_input("test*") == "test"

    def test_angle_brackets_removed(self):
        assert _sanitize_tsquery_input("<hello>") == "hello"

    def test_all_operators_returns_empty(self):
        assert _sanitize_tsquery_input("!!!") == ""

    def test_only_whitespace_returns_empty(self):
        assert _sanitize_tsquery_input("   ") == ""

    def test_mixed_operators_and_whitespace_returns_empty(self):
        assert _sanitize_tsquery_input("& | !") == ""

    def test_normal_chinese_unchanged(self):
        assert _sanitize_tsquery_input("正常中文") == "正常中文"

    def test_normal_english_unchanged(self):
        assert _sanitize_tsquery_input("hello world") == "hello world"

    def test_mixed_operators_cleaned(self):
        assert _sanitize_tsquery_input("a & b | c") == "a b c"

    def test_multiple_spaces_collapsed(self):
        assert _sanitize_tsquery_input("hello    world") == "hello world"

    def test_leading_trailing_whitespace_stripped(self):
        assert _sanitize_tsquery_input("  hello  ") == "hello"


class TestBuildTsquery:
    """Tests for _build_tsquery function (T-36-02)."""

    def test_normal_input(self):
        result = _build_tsquery("hello world")
        assert result == "hello world"

    def test_special_chars_cleaned(self):
        result = _build_tsquery("hello&world")
        assert "&" not in result
        assert "hello" in result
        assert "world" in result

    def test_all_operators_returns_empty(self):
        assert _build_tsquery("!!!") == ""

    def test_empty_string(self):
        assert _build_tsquery("") == ""

    def test_whitespace_only(self):
        assert _build_tsquery("   ") == ""

    def test_tab_newline(self):
        assert _build_tsquery("\t\n") == ""

    def test_mixed_whitespace_and_operators(self):
        assert _build_tsquery("  & \t | \n ") == ""
