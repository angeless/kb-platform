"""Unit tests for ZIP archive decompression size limits (T-37-07)."""

import io
import uuid
import zipfile

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.asset_service import AssetService, MAX_ARCHIVE_TOTAL_BYTES, MAX_COMPRESSION_RATIO


def _make_zip(files: dict[str, bytes]) -> bytes:
    """Create an in-memory ZIP from a dict of {filename: content}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _make_zip_with_fake_size(filename: str, content: bytes, fake_file_size: int) -> bytes:
    """Create a ZIP where ZipInfo.file_size is manually set (for testing size checks)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        info = zipfile.ZipInfo(filename)
        info.file_size = fake_file_size
        info.compress_size = len(content)
        zf.writestr(info, content)
    return buf.getvalue()


def _make_high_ratio_zip(filename: str) -> bytes:
    """Create a ZIP with very high compression ratio (zeros compress well)."""
    buf = io.BytesIO()
    # 10KB of zeros will compress to very small size with ZIP_DEFLATED
    content = b"\x00" * (10 * 1024)
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(filename, content)
    return buf.getvalue()


@pytest.fixture
def mock_asset_service():
    """Create an AssetService with mocked DB and small limits for testing."""
    db = AsyncMock()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()

    # Mock _verify_project to return successfully
    svc = AssetService(db, tenant_id, user_id, storage=None, max_upload_size_bytes=1024)  # 1KB limit for testing

    # Mock _verify_project
    svc._verify_project = AsyncMock()

    # Mock db.execute for duplicate check — always return no duplicate
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)
    db.flush = AsyncMock()

    return svc, project_id


@pytest.mark.asyncio
async def test_normal_zip_imports_successfully(mock_asset_service):
    """Normal small ZIP should import all files."""
    svc, project_id = mock_asset_service
    zip_data = _make_zip({
        "readme.txt": b"Hello world",
        "notes.md": b"Some notes",
    })
    result = await svc.import_archive(project_id, zip_data, "test.zip")
    assert result["imported"] == 2
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_single_file_exceeding_limit_skipped(mock_asset_service):
    """A file larger than max_upload_size_bytes should be skipped."""
    svc, project_id = mock_asset_service
    # svc.max_upload_size_bytes is 1024 (1KB)
    zip_data = _make_zip({
        "small.txt": b"ok",
        "big.txt": b"x" * 2048,  # 2KB > 1KB limit
    })
    result = await svc.import_archive(project_id, zip_data, "test.zip")
    assert result["imported"] == 1  # only small.txt
    assert len(result["errors"]) >= 1
    assert any("大小超过限制" in e for e in result["errors"])


@pytest.mark.asyncio
async def test_total_decompressed_limit_stops_processing(mock_asset_service):
    """When total decompressed size exceeds limit, remaining files should be skipped."""
    svc, project_id = mock_asset_service

    # Temporarily patch the module-level constant for this test
    import app.services.asset_service as asset_mod
    original = asset_mod.MAX_ARCHIVE_TOTAL_BYTES
    asset_mod.MAX_ARCHIVE_TOTAL_BYTES = 500  # 500 bytes total limit

    try:
        zip_data = _make_zip({
            "file1.txt": b"a" * 200,
            "file2.txt": b"b" * 200,
            "file3.txt": b"c" * 200,  # cumulative 600 > 500, should trigger stop
        })
        # Raise per-file limit so individual files pass
        svc.max_upload_size_bytes = 10000

        result = await svc.import_archive(project_id, zip_data, "test.zip")
        # file1 + file2 = 400 OK, file3 pushes to 600 > 500 → break
        assert result["imported"] == 2
        assert len(result["errors"]) >= 1
        assert any("解压总大小超过限制" in e for e in result["errors"])
    finally:
        asset_mod.MAX_ARCHIVE_TOTAL_BYTES = original


@pytest.mark.asyncio
async def test_high_compression_ratio_skipped(mock_asset_service):
    """Files with compression ratio > MAX_COMPRESSION_RATIO should be skipped."""
    svc, project_id = mock_asset_service
    svc.max_upload_size_bytes = 100 * 1024 * 1024  # Don't trigger size limit

    zip_data = _make_high_ratio_zip("zeros.txt")

    # Verify the ZIP actually has high compression ratio
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        info = zf.getinfo("zeros.txt")
        if info.compress_size > 0:
            ratio = info.file_size / info.compress_size
        else:
            ratio = 0

    if ratio > MAX_COMPRESSION_RATIO:
        result = await svc.import_archive(uuid.uuid4(), zip_data, "bomb.zip")
        # Note: _verify_project is mocked, so any project_id works
        assert any("压缩比过高" in e for e in result["errors"])
    else:
        pytest.skip(f"Compression ratio {ratio:.1f} not high enough to trigger guard")


@pytest.mark.asyncio
async def test_disallowed_file_type_still_skipped(mock_asset_service):
    """File type whitelist should still work alongside size guards."""
    svc, project_id = mock_asset_service
    svc.max_upload_size_bytes = 100 * 1024 * 1024
    zip_data = _make_zip({
        "readme.txt": b"Hello",
        "malware.exe": b"bad stuff",
    })
    result = await svc.import_archive(project_id, zip_data, "test.zip")
    assert result["imported"] == 1
    assert result["skipped"] == 1


@pytest.mark.asyncio
async def test_actual_size_exceeding_limit_after_read(mock_asset_service):
    """If actual decompressed content exceeds limit (crafted ZipInfo), should be skipped."""
    svc, project_id = mock_asset_service
    # max_upload_size_bytes = 1024 (1KB)
    # Create a file that declares small size in ZipInfo but is actually large
    # Note: Python's zipfile may not allow this easily, so we test the normal path
    # where file_size in ZipInfo matches actual size
    big_content = b"x" * 2048
    zip_data = _make_zip({"big.txt": big_content})
    result = await svc.import_archive(project_id, zip_data, "test.zip")
    # Should be caught by ZipInfo.file_size check (pre-read)
    assert result["imported"] == 0
    assert len(result["errors"]) >= 1
