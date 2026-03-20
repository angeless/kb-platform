"""Tests for T-37-02: Upload transaction order and MinIO cleanup.

Verifies that:
1. MinIO upload happens before DB record creation (source validation)
2. DB flush failure triggers best-effort MinIO cleanup
3. delete_file is best-effort (logs warning, doesn't raise)
"""

import inspect
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared_errors import ConflictException


def _make_asset_service(storage=None):
    """Create an AssetService with mocked DB and optional storage."""
    from app.services.asset_service import AssetService

    svc = AssetService.__new__(AssetService)
    svc.db = AsyncMock()
    svc.tenant_id = uuid.uuid4()
    svc.user_id = uuid.uuid4()
    svc.storage = storage
    svc.max_upload_size_bytes = 100 * 1024 * 1024
    svc._verify_project = AsyncMock()
    svc.db.add = MagicMock()
    return svc


class TestUploadTransactionOrder:
    """MinIO upload must happen before DB record creation."""

    def test_upload_source_minio_before_db(self):
        """In upload(), storage.upload_file appears before db.add in source."""
        from app.services.asset_service import AssetService

        source = inspect.getsource(AssetService.upload)
        minio_pos = source.find("storage.upload_file")
        db_add_pos = source.find("self.db.add")

        assert minio_pos != -1
        assert db_add_pos != -1
        assert minio_pos < db_add_pos, "MinIO upload must come before db.add"

    def test_import_url_source_minio_before_db(self):
        """In import_url(), storage.upload_file appears before db.add in source."""
        from app.services.asset_service import AssetService

        source = inspect.getsource(AssetService.import_url)
        minio_pos = source.find("storage.upload_file")
        db_add_pos = source.find("self.db.add")

        assert minio_pos != -1
        assert db_add_pos != -1
        assert minio_pos < db_add_pos


class TestUploadFlushFailureCleanup:
    """DB flush failure should trigger MinIO cleanup."""

    @pytest.mark.asyncio
    async def test_upload_flush_fail_cleans_minio(self):
        storage = MagicMock()
        storage.upload_file = MagicMock(return_value="key")
        storage.delete_file = MagicMock()

        svc = _make_asset_service(storage=storage)
        # First execute: hash dup check returns None (no dup)
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        # flush raises exception (e.g., IntegrityError)
        svc.db.flush = AsyncMock(side_effect=Exception("IntegrityError"))

        with pytest.raises(Exception, match="IntegrityError"):
            await svc.upload(
                project_id=uuid.uuid4(),
                filename="test.pdf",
                asset_type="pdf",
                file_content=b"test content",
            )

        # storage.upload_file should have been called
        storage.upload_file.assert_called_once()
        # storage.delete_file should have been called for cleanup
        storage.delete_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_flush_success_no_cleanup(self):
        storage = MagicMock()
        storage.upload_file = MagicMock(return_value="key")
        storage.delete_file = MagicMock()

        svc = _make_asset_service(storage=storage)
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        svc.db.flush = AsyncMock()

        await svc.upload(
            project_id=uuid.uuid4(),
            filename="test.pdf",
            asset_type="pdf",
            file_content=b"test content",
        )

        storage.upload_file.assert_called_once()
        storage.delete_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_no_storage_flush_fail_no_error(self):
        """When storage is None, flush failure should not cause secondary error."""
        svc = _make_asset_service(storage=None)
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        svc.db.flush = AsyncMock(side_effect=Exception("DB error"))

        with pytest.raises(Exception, match="DB error"):
            await svc.upload(
                project_id=uuid.uuid4(),
                filename="test.txt",
                asset_type="text",
                file_content=b"content",
            )


class TestImportUrlFlushFailureCleanup:
    """import_url DB flush failure should trigger MinIO cleanup."""

    @pytest.mark.asyncio
    async def test_import_url_flush_fail_cleans_minio(self):
        storage = MagicMock()
        storage.upload_file = MagicMock(return_value="key")
        storage.delete_file = MagicMock()

        svc = _make_asset_service(storage=storage)
        svc.db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        svc.db.flush = AsyncMock(side_effect=Exception("IntegrityError"))

        with patch("app.utils.url_fetcher.fetch_url", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (b"url content", "text/html")

            with pytest.raises(Exception, match="IntegrityError"):
                await svc.import_url(project_id=uuid.uuid4(), url="https://example.com/page")

        storage.upload_file.assert_called_once()
        storage.delete_file.assert_called_once()


class TestDeleteFileBestEffort:
    """StorageClient.delete_file must be best-effort."""

    def test_delete_file_exists_in_storage_client(self):
        """StorageClient must have a delete_file method."""
        from app.utils.storage import StorageClient

        assert hasattr(StorageClient, "delete_file")

    def test_delete_file_source_has_try_except(self):
        """delete_file must have try/except for best-effort behavior."""
        from app.utils.storage import StorageClient

        source = inspect.getsource(StorageClient.delete_file)
        assert "try:" in source
        assert "except" in source
        assert "warning" in source.lower()
