"""Asset service: upload, list, get with tenant isolation."""

import hashlib
import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import AppException, ConflictException, ErrorCode, NotFoundException
from shared_models import Asset

from app.utils.storage import PARSEABLE_ASSET_TYPES, StorageClient, is_allowed_file

from . import TenantService

logger = logging.getLogger(__name__)

# ZIP archive decompression limits (DoS protection)
MAX_ARCHIVE_TOTAL_BYTES = 500 * 1024 * 1024  # 500MB total decompressed
MAX_COMPRESSION_RATIO = 100  # skip files with ratio > 100
MAX_ARCHIVE_FILES = 200  # max files in archive (M-04)
MAX_ARCHIVE_DEPTH = 5  # max directory nesting depth (M-04)


class AssetService(TenantService):
    """Operations for assets, scoped to a single tenant via project ownership."""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        storage: StorageClient | None = None,
        max_upload_size_bytes: int = 100 * 1024 * 1024,
    ) -> None:
        super().__init__(db, tenant_id)
        self.user_id = user_id
        self.storage = storage
        self.max_upload_size_bytes = max_upload_size_bytes

    async def upload(
        self,
        project_id: uuid.UUID,
        filename: str,
        asset_type: str,
        file_content: bytes,
        content_type: str = "application/octet-stream",
    ) -> Asset:
        """Upload a file asset. Validate, compute SHA-256, check duplicate, store to MinIO, create record."""
        await self._verify_project(project_id)

        # Validate file extension
        if not is_allowed_file(filename):
            raise AppException(
                error_code=ErrorCode.ASSET_TYPE_NOT_ALLOWED,
                message=f"文件类型不允许: {filename}",
            )

        # Validate file size
        if len(file_content) > self.max_upload_size_bytes:
            raise AppException(
                error_code=ErrorCode.ASSET_TOO_LARGE,
                message=f"文件大小超过限制 ({self.max_upload_size_bytes // (1024 * 1024)}MB)",
            )

        file_hash = hashlib.sha256(file_content).hexdigest()

        # Check duplicate
        dup_q = select(Asset).where(
            Asset.project_id == project_id,
            Asset.file_hash == file_hash,
        )
        dup = (await self.db.execute(dup_q)).scalar_one_or_none()
        if dup is not None:
            raise ConflictException(
                error_code=ErrorCode.ASSET_DUPLICATE_HASH,
                message="文件已存在（重复上传）",
            )

        asset_id = uuid.uuid4()
        object_path = f"{self.tenant_id}/{project_id}/{asset_id}/{filename}"

        # Upload to MinIO/S3 if storage client is available
        if self.storage is not None:
            self.storage.upload_file(object_path, file_content, content_type)

        initial_parse_status = "pending" if asset_type in PARSEABLE_ASSET_TYPES else "unsupported"

        asset = Asset(
            id=asset_id,
            project_id=project_id,
            asset_type=asset_type,
            filename=filename,
            object_path=object_path,
            file_hash=file_hash,
            file_size=len(file_content),
            parse_status=initial_parse_status,
            uploaded_by=self.user_id,
        )
        self.db.add(asset)
        try:
            await self.db.flush()
        except Exception:
            # DB flush failed — best-effort cleanup of uploaded MinIO file
            if self.storage is not None:
                self.storage.delete_file(object_path)
            raise
        return asset

    async def import_url(self, project_id: uuid.UUID, url: str) -> Asset:
        """Import a URL as an asset. Fetches content, stores to MinIO, creates record.

        The actual URL fetching is done by the caller (router layer) to keep
        the service layer synchronous w.r.t. external HTTP calls. This method
        receives the already-fetched content.
        """
        await self._verify_project(project_id)

        # Validate URL against SSRF (DNS resolution check)
        from app.utils.url_validator import validate_import_url
        validate_import_url(url)

        # Use URL fetcher to download content
        from app.utils.url_fetcher import fetch_url
        content, content_type = await fetch_url(url)

        file_hash = hashlib.sha256(content).hexdigest()

        # Check duplicate
        dup_q = select(Asset).where(
            Asset.project_id == project_id,
            Asset.file_hash == file_hash,
        )
        dup = (await self.db.execute(dup_q)).scalar_one_or_none()
        if dup is not None:
            raise ConflictException(
                error_code=ErrorCode.ASSET_DUPLICATE_HASH,
                message="该 URL 内容已存在（重复哈希）",
            )

        # Derive filename from URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        filename = parsed.path.rstrip("/").split("/")[-1] or "index.html"
        if "." not in filename:
            filename += ".html"

        asset_id = uuid.uuid4()
        object_path = f"{self.tenant_id}/{project_id}/{asset_id}/{filename}"

        # Upload to MinIO/S3
        if self.storage is not None:
            self.storage.upload_file(object_path, content, content_type)

        asset = Asset(
            id=asset_id,
            project_id=project_id,
            asset_type="url",
            filename=filename,
            source_url=url,
            object_path=object_path,
            file_hash=file_hash,
            file_size=len(content),
            parse_status="pending",
            uploaded_by=self.user_id,
        )
        self.db.add(asset)
        try:
            await self.db.flush()
        except Exception:
            # DB flush failed — best-effort cleanup of uploaded MinIO file
            if self.storage is not None:
                self.storage.delete_file(object_path)
            raise
        return asset

    async def import_archive(
        self, project_id: uuid.UUID, archive_content: bytes, archive_filename: str
    ) -> dict:
        """Import a ZIP archive: extract files and create individual Asset records.

        Returns dict with imported/skipped/errors counts.
        """
        import io
        import os
        import zipfile

        await self._verify_project(project_id)

        if not zipfile.is_zipfile(io.BytesIO(archive_content)):
            raise AppException(
                error_code=ErrorCode.ASSET_TYPE_NOT_ALLOWED,
                message="文件不是有效的 ZIP 压缩包",
            )

        imported = 0
        skipped = 0
        errors: list[str] = []

        with zipfile.ZipFile(io.BytesIO(archive_content), "r") as zf:
            entries = [e for e in zf.namelist() if not e.endswith("/")]  # skip directories
            if len(entries) > MAX_ARCHIVE_FILES:
                raise AppException(
                    error_code=ErrorCode.ASSET_TOO_LARGE,
                    message=f"压缩包内文件数超过限制 ({MAX_ARCHIVE_FILES})",
                )

            # Directory depth check (M-04)
            from pathlib import PurePosixPath
            for entry_name in entries:
                depth = len(PurePosixPath(entry_name).parts)
                if depth > MAX_ARCHIVE_DEPTH:
                    raise AppException(
                        error_code=ErrorCode.ASSET_TOO_LARGE,
                        message=f"压缩包目录嵌套层数超过限制 ({MAX_ARCHIVE_DEPTH} 层): {entry_name}",
                    )

            # Security: check ALL entries for path traversal before processing any
            for entry_name in entries:
                normalized = os.path.normpath(entry_name)
                if ".." in normalized.split(os.sep) or normalized.startswith("/"):
                    raise AppException(
                        error_code=ErrorCode.ASSET_TYPE_NOT_ALLOWED,
                        message=f"ZIP 文件包含非法路径（路径穿越）: {entry_name}",
                    )

            total_decompressed = 0

            for entry_name in entries:
                # Extract safe filename (basename after normpath)
                normalized = os.path.normpath(entry_name)
                filename = os.path.basename(normalized)
                if not filename:
                    continue

                # Check file type whitelist
                if not is_allowed_file(filename):
                    skipped += 1
                    continue

                # --- Size guards (T-37-07) ---
                info = zf.getinfo(entry_name)

                # Compression ratio check
                if info.compress_size > 0 and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                    logger.warning("ZIP entry %s skipped: compression ratio %.1f exceeds limit %d",
                                   entry_name, info.file_size / info.compress_size, MAX_COMPRESSION_RATIO)
                    errors.append(f"{entry_name}: 压缩比过高（疑似 ZIP 炸弹），已跳过")
                    continue

                # Single file size check
                if info.file_size > self.max_upload_size_bytes:
                    errors.append(f"{entry_name}: 文件解压后大小超过限制 ({self.max_upload_size_bytes // (1024 * 1024)}MB)，已跳过")
                    continue

                # Total decompressed size check
                total_decompressed += info.file_size
                if total_decompressed > MAX_ARCHIVE_TOTAL_BYTES:
                    errors.append(f"解压总大小超过限制 ({MAX_ARCHIVE_TOTAL_BYTES // (1024 * 1024)}MB)，剩余文件已跳过")
                    break

                try:
                    file_content = zf.read(entry_name)
                except Exception as e:
                    errors.append(f"{entry_name}: {e!s}")
                    continue

                # Verify actual size matches declared size (defend against crafted ZipInfo)
                if len(file_content) > self.max_upload_size_bytes:
                    errors.append(f"{entry_name}: 实际解压大小超过限制，已跳过")
                    continue

                file_hash = hashlib.sha256(file_content).hexdigest()

                # Check duplicate
                dup_q = select(Asset).where(
                    Asset.project_id == project_id,
                    Asset.file_hash == file_hash,
                )
                dup = (await self.db.execute(dup_q)).scalar_one_or_none()
                if dup is not None:
                    skipped += 1
                    continue

                asset_id = uuid.uuid4()
                object_path = f"{self.tenant_id}/{project_id}/{asset_id}/{filename}"

                if self.storage is not None:
                    self.storage.upload_file(object_path, file_content)

                from app.utils.storage import guess_asset_type
                guessed_type = guess_asset_type(filename)
                asset = Asset(
                    id=asset_id,
                    project_id=project_id,
                    asset_type=guessed_type,
                    filename=filename,
                    object_path=object_path,
                    file_hash=file_hash,
                    file_size=len(file_content),
                    parse_status="pending" if guessed_type in PARSEABLE_ASSET_TYPES else "unsupported",
                    uploaded_by=self.user_id,
                )
                self.db.add(asset)
                imported += 1

        await self.db.flush()
        return {"imported": imported, "skipped": skipped, "errors": errors}

    async def list(
        self, project_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[Asset], int]:
        """Return paginated assets for a project."""
        await self._verify_project(project_id)

        base = select(Asset).where(Asset.project_id == project_id)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = base.order_by(Asset.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()

        return list(rows), total

    async def get(self, asset_id: uuid.UUID) -> Asset:
        """Get a single asset by ID. Verify via project->tenant chain."""
        q = select(Asset).where(Asset.id == asset_id)
        result = await self.db.execute(q)
        asset = result.scalar_one_or_none()
        if asset is None:
            raise NotFoundException(
                error_code=ErrorCode.ASSET_NOT_FOUND,
                message="资料不存在",
            )
        await self._verify_project(asset.project_id)
        return asset
