"""Integration tests for URL import with readability extraction (v0.48.2)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.asset_service import AssetService


NEWS_HTML = b"""
<html>
<head><title>Breaking News</title></head>
<body>
    <nav><a href="/">Home</a><a href="/about">About</a></nav>
    <article>
        <h1>Major Scientific Breakthrough</h1>
        <p>Researchers at a leading university have announced a major scientific
        breakthrough that could revolutionize the field of renewable energy.
        The discovery involves a novel catalytic process.</p>
        <p>The findings were published in Nature and have been independently
        verified by three separate laboratories across different continents.</p>
    </article>
    <footer>Copyright 2026</footer>
    <script>trackPageView();</script>
</body>
</html>
"""


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    db.flush = AsyncMock()
    # Track added objects
    db._added = []
    original_add = db.add

    def track_add(obj):
        db._added.append(obj)
    db.add = track_add
    return db


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.upload_file = MagicMock()
    storage.delete_file = MagicMock()
    return storage


@pytest.fixture
def service(mock_db, mock_storage):
    kb_id = uuid.uuid4()
    user_id = uuid.uuid4()
    return AssetService(
        db=mock_db,
        kb_id=kb_id,
        user_id=user_id,
        storage=mock_storage,
    )


class TestUrlImportWithReadability:
    """Tests for URL import with readability extraction."""

    @pytest.mark.asyncio
    @patch("app.utils.url_validator.validate_import_url", new_callable=AsyncMock)
    @patch("app.utils.url_fetcher.fetch_url", new_callable=AsyncMock)
    async def test_extracted_text_in_chunk(self, mock_fetch, mock_validate, service, mock_db):
        """AC-1: Imported URL → AssetChunk.content_text is plain text, not HTML."""
        mock_fetch.return_value = (NEWS_HTML, "text/html")
        project_id = uuid.uuid4()

        with patch.object(service, "_verify_project", new_callable=AsyncMock):
            asset = await service.import_url(project_id, "https://news.example.com/article")

        # Find the AssetChunk among added objects
        chunks = [obj for obj in mock_db._added if hasattr(obj, "chunk_index")]
        assert len(chunks) == 1

        chunk = chunks[0]
        assert "<nav>" not in chunk.content_text
        assert "<script>" not in chunk.content_text
        assert "trackPageView" not in chunk.content_text
        assert "breakthrough" in chunk.content_text

    @pytest.mark.asyncio
    @patch("app.utils.url_validator.validate_import_url", new_callable=AsyncMock)
    @patch("app.utils.url_fetcher.fetch_url", new_callable=AsyncMock)
    async def test_raw_html_stored_in_minio(self, mock_fetch, mock_validate, service, mock_storage):
        """AC-2: MinIO receives the raw HTML (not extracted text)."""
        mock_fetch.return_value = (NEWS_HTML, "text/html")
        project_id = uuid.uuid4()

        with patch.object(service, "_verify_project", new_callable=AsyncMock):
            await service.import_url(project_id, "https://news.example.com/article")

        mock_storage.upload_file.assert_called_once()
        stored_content = mock_storage.upload_file.call_args[0][1]
        assert stored_content == NEWS_HTML  # Raw HTML preserved

    @pytest.mark.asyncio
    @patch("app.utils.url_validator.validate_import_url", new_callable=AsyncMock)
    @patch("app.utils.url_fetcher.fetch_url", new_callable=AsyncMock)
    async def test_metadata_in_chunk_tags(self, mock_fetch, mock_validate, service, mock_db):
        """AC-3: AssetChunk.tags contains extracted metadata."""
        mock_fetch.return_value = (NEWS_HTML, "text/html")
        project_id = uuid.uuid4()

        with patch.object(service, "_verify_project", new_callable=AsyncMock):
            await service.import_url(project_id, "https://news.example.com/article")

        chunks = [obj for obj in mock_db._added if hasattr(obj, "chunk_index")]
        assert len(chunks) == 1

        tags = chunks[0].tags
        assert "extracted_title" in tags
        assert "extracted_author" in tags
        assert "extracted_date" in tags
        assert tags["source"] == "readability"

    @pytest.mark.asyncio
    @patch("app.utils.url_validator.validate_import_url", new_callable=AsyncMock)
    @patch("app.utils.url_fetcher.fetch_url", new_callable=AsyncMock)
    async def test_unparseable_url_fallback(self, mock_fetch, mock_validate, service, mock_db):
        """AC-4: Unparseable URL → fallback to stripped text, no error."""
        # Minimal HTML that trafilatura likely won't extract
        minimal_html = b"<div>Just some short text.</div>"
        mock_fetch.return_value = (minimal_html, "text/html")
        project_id = uuid.uuid4()

        with patch.object(service, "_verify_project", new_callable=AsyncMock):
            asset = await service.import_url(project_id, "https://example.com/page")

        # Should not raise; chunk should have some text
        chunks = [obj for obj in mock_db._added if hasattr(obj, "chunk_index")]
        assert len(chunks) == 1
        assert len(chunks[0].content_text) > 0
        assert "<div>" not in chunks[0].content_text

    @pytest.mark.asyncio
    @patch("app.utils.url_validator.validate_import_url", new_callable=AsyncMock)
    @patch("app.utils.url_fetcher.fetch_url", new_callable=AsyncMock)
    async def test_ssrf_validation_still_called(self, mock_fetch, mock_validate, service):
        """AC-5: SSRF validation is still called before fetching."""
        mock_fetch.return_value = (b"<html><body>Hi</body></html>", "text/html")
        project_id = uuid.uuid4()

        with patch.object(service, "_verify_project", new_callable=AsyncMock):
            await service.import_url(project_id, "https://example.com")

        mock_validate.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    @patch("app.utils.url_validator.validate_import_url", new_callable=AsyncMock)
    @patch("app.utils.url_fetcher.fetch_url", new_callable=AsyncMock)
    async def test_parse_status_is_completed(self, mock_fetch, mock_validate, service, mock_db):
        """URL import sets parse_status to completed (no worker re-processing needed)."""
        mock_fetch.return_value = (NEWS_HTML, "text/html")
        project_id = uuid.uuid4()

        with patch.object(service, "_verify_project", new_callable=AsyncMock):
            asset = await service.import_url(project_id, "https://news.example.com/article")

        assert asset.parse_status == "completed"
