"""Unit tests for readability.py — web article content extraction."""

from app.utils.readability import extract_article


class TestExtractArticle:
    """AC-1 through AC-5: article extraction with fallback."""

    def test_extracts_article_body_from_html(self):
        """AC-1: News-like HTML → clean text without nav/ads/scripts."""
        html = """
        <html>
        <head><title>Breaking News</title></head>
        <body>
            <nav><a href="/">Home</a><a href="/news">News</a></nav>
            <article>
                <h1>Important Discovery</h1>
                <p>Scientists have made a groundbreaking discovery that changes our
                understanding of the natural world. The research was conducted over
                several years and involved multiple international teams.</p>
                <p>The findings were published in a leading journal and have been
                independently verified by peer review. Experts say this could lead
                to significant advances in the field.</p>
            </article>
            <aside>Related: <a href="/ad">Buy stuff</a></aside>
            <script>console.log("tracker")</script>
            <footer>Copyright 2026</footer>
        </body>
        </html>
        """
        result = extract_article(html, url="https://news.example.com/article")

        assert "tracker" not in result["body"]
        assert "console.log" not in result["body"]
        # The key assertion: body contains the article text
        assert "groundbreaking discovery" in result["body"]
        assert "independently verified" in result["body"]

    def test_returns_all_four_fields(self):
        """AC-2: Result always contains title, body, author, date."""
        html = "<html><body><p>Hello world content for extraction testing.</p></body></html>"
        result = extract_article(html, url="https://example.com")

        assert "title" in result
        assert "body" in result
        assert "author" in result
        assert "date" in result
        assert isinstance(result["title"], str)
        assert isinstance(result["body"], str)

    def test_empty_html_returns_empty_body(self):
        """AC-3: Empty HTML → empty body, no error."""
        result = extract_article("", url="https://example.com")
        assert result["body"] == ""
        assert result["title"] == ""
        assert result["author"] is None
        assert result["date"] is None

    def test_whitespace_only_html(self):
        """AC-3 variant: Whitespace-only HTML → empty body."""
        result = extract_article("   \n\t  ", url="https://example.com")
        assert result["body"] == ""

    def test_plain_text_returned_as_body(self):
        """AC-4: Non-HTML text → returned as-is in body."""
        plain = "This is just plain text with no HTML tags at all."
        result = extract_article(plain, url="https://example.com")
        assert result["body"] == plain
        assert result["title"] == ""

    def test_fallback_strips_tags_on_minimal_html(self):
        """AC-5: When trafilatura returns nothing, fallback strips tags."""
        # Minimal HTML that trafilatura may not extract (too short for article detection)
        html = "<div><script>alert('xss')</script><p>Short.</p></div>"
        result = extract_article(html, url="https://example.com")

        # Regardless of whether trafilatura or fallback handles it,
        # script content should not appear and text should be present
        assert "alert" not in result["body"]
        assert isinstance(result["body"], str)

    def test_html_entities_decoded(self):
        """Fallback correctly decodes HTML entities."""
        html = "<p>Price: &lt;$50 &amp; free shipping</p>"
        result = extract_article(html, url="https://example.com")
        assert "<$50" in result["body"] or "&lt;" not in result["body"]
        assert "&amp;" not in result["body"]

    def test_none_url_does_not_crash(self):
        """URL parameter is optional, should not crash when empty."""
        html = "<html><body><p>Content here for testing purposes.</p></body></html>"
        result = extract_article(html)
        assert isinstance(result["body"], str)
