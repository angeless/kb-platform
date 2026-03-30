"""Batch import service: ZIP upload → individual assets → optional Celery dispatch."""

from __future__ import annotations

import hashlib
import io
import logging
import os
import uuid
import zipfile
from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import AppException, ErrorCode, NotFoundException
from shared_models import Asset, BatchImport, BatchImportAsset, Job

from . import TenantService

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".pdf", ".docx",
    ".jpg", ".jpeg", ".png",
    ".mp3", ".wav", ".m4a", ".flac",
}
PARSEABLE_TYPES = {"text", "pdf", "doc", "image", "audio"}
MAX_ZIP_SIZE = 500 * 1024 * 1024  # 500MB
MAX_FILES = 200
MAX_DEPTH = 3
MAX_COMPRESSION_RATIO = 100

_celery_app = None


def _get_celery_app():
    global _celery_app
    if _celery_app is None:
        try:
            from celery import Celery
            from shared_config.settings import get_settings
            settings = get_settings()
            _celery_app = Celery(broker=settings.redis_url)
        except Exception:
            logger.warning("Celery not available for batch import")
    return _celery_app


def _guess_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext in {".jpg", ".jpeg", ".png"}:
        return "image"
    if ext in {".mp3", ".wav", ".m4a", ".flac"}:
        return "audio"
    if ext == ".pdf":
        return "pdf"
    if ext == ".docx":
        return "doc"
    return "text"


class BatchImportService(TenantService):
    def __init__(
        self,
        db: AsyncSession,
        kb_id: uuid.UUID,
        user_id: uuid.UUID,
        storage,
    ) -> None:
        super().__init__(db, kb_id)
        self.user_id = user_id
        self.storage = storage

    async def create_batch(
        self,
        project_id: uuid.UUID,
        archive_content: bytes,
        archive_filename: str,
        auto_start: bool = True,
    ) -> dict:
        """Process ZIP, create batch + asset records, optionally dispatch Celery tasks."""
        await self._verify_project(project_id)

        if len(archive_content) > MAX_ZIP_SIZE:
            raise AppException(
                error_code=ErrorCode.ASSET_TOO_LARGE,
                message=f"文件大小超过限制 ({MAX_ZIP_SIZE // (1024 * 1024)}MB)",
            )

        if not zipfile.is_zipfile(io.BytesIO(archive_content)):
            raise AppException(
                error_code=ErrorCode.ASSET_TYPE_NOT_ALLOWED,
                message="文件不是有效的 ZIP 压缩包",
            )

        batch_id = uuid.uuid4()
        zip_path = f"{self.kb_id}/{project_id}/batches/{batch_id}/original.zip"

        # Upload ZIP to MinIO
        if self.storage is not None:
            self.storage.upload_file(zip_path, archive_content, "application/zip")

        imported_assets: list[tuple[uuid.UUID, str]] = []  # (asset_id, original_filename)
        skipped = 0

        with zipfile.ZipFile(io.BytesIO(archive_content), "r") as zf:
            entries = [e for e in zf.namelist() if not e.endswith("/")]
            if len(entries) > MAX_FILES:
                raise AppException(
                    error_code=ErrorCode.ASSET_TOO_LARGE,
                    message=f"压缩包内文件数超过限制 ({MAX_FILES})",
                )

            # Security checks
            for entry_name in entries:
                depth = len(PurePosixPath(entry_name).parts)
                if depth > MAX_DEPTH:
                    raise AppException(
                        error_code=ErrorCode.ASSET_TOO_LARGE,
                        message=f"压缩包目录嵌套层数超过限制 ({MAX_DEPTH} 层)",
                    )
                normalized = os.path.normpath(entry_name)
                if ".." in normalized.split(os.sep) or normalized.startswith("/"):
                    raise AppException(
                        error_code=ErrorCode.ASSET_TYPE_NOT_ALLOWED,
                        message=f"ZIP 文件包含非法路径: {entry_name}",
                    )

            for entry_name in entries:
                normalized = os.path.normpath(entry_name)
                filename = os.path.basename(normalized)
                if not filename or filename.startswith("."):
                    skipped += 1
                    continue

                ext = os.path.splitext(filename)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    skipped += 1
                    continue

                info = zf.getinfo(entry_name)
                if info.compress_size > 0 and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                    skipped += 1
                    continue

                try:
                    file_content = zf.read(entry_name)
                except Exception:
                    skipped += 1
                    continue

                file_hash = hashlib.sha256(file_content).hexdigest()

                # Skip duplicates
                dup_q = select(Asset).where(
                    Asset.project_id == project_id,
                    Asset.file_hash == file_hash,
                )
                if (await self.db.execute(dup_q)).scalar_one_or_none() is not None:
                    skipped += 1
                    continue

                asset_id = uuid.uuid4()
                object_path = f"{self.kb_id}/{project_id}/{asset_id}/{filename}"

                if self.storage is not None:
                    self.storage.upload_file(object_path, file_content)

                guessed_type = _guess_type(filename)
                asset = Asset(
                    id=asset_id,
                    project_id=project_id,
                    asset_type=guessed_type,
                    filename=filename,
                    object_path=object_path,
                    file_hash=file_hash,
                    file_size=len(file_content),
                    parse_status="pending" if guessed_type in PARSEABLE_TYPES else "unsupported",
                    uploaded_by=self.user_id,
                )
                self.db.add(asset)
                imported_assets.append((asset_id, entry_name))

        if len(imported_assets) == 0:
            raise AppException(
                error_code=ErrorCode.EMPTY_ARCHIVE,
                message="压缩包中没有支持的文件格式",
            )

        # Create batch record
        batch = BatchImport(
            id=batch_id,
            project_id=project_id,
            created_by=self.user_id,
            zip_path=zip_path,
            total_files=len(imported_assets),
            status="processing" if auto_start else "pending",
        )
        self.db.add(batch)

        # Create batch-asset links
        for asset_id, original_filename in imported_assets:
            link = BatchImportAsset(
                id=uuid.uuid4(),
                batch_id=batch_id,
                asset_id=asset_id,
                original_filename=original_filename,
            )
            self.db.add(link)

        await self.db.flush()

        # Dispatch Celery tasks
        if auto_start:
            celery = _get_celery_app()
            if celery is not None:
                for asset_id, _ in imported_assets:
                    # Create a job record for each asset
                    job = Job(
                        id=uuid.uuid4(),
                        project_id=project_id,
                        job_type="ingest",
                        status="pending",
                        retry_count=0,
                        created_by=self.user_id,
                    )
                    self.db.add(job)
                    await self.db.flush()
                    try:
                        result = celery.send_task(
                            "ingestion.parse_asset",
                            args=[str(asset_id), str(job.id)],
                        )
                        job.celery_task_id = result.id
                    except Exception as e:
                        logger.warning("Failed to dispatch task for asset %s: %s", asset_id, e)
                await self.db.flush()

        return {
            "batch_id": batch_id,
            "total_files": len(imported_assets),
            "skipped_files": skipped,
        }

    async def get_batch(self, batch_id: uuid.UUID) -> dict:
        """Get batch status with per-file parse_status."""
        q = select(BatchImport).where(BatchImport.id == batch_id)
        result = await self.db.execute(q)
        batch = result.scalar_one_or_none()
        if batch is None:
            raise NotFoundException(
                error_code=ErrorCode.BATCH_NOT_FOUND,
                message="批次不存在",
            )

        # Verify tenant via project
        await self._verify_project(batch.project_id)

        # Get asset parse statuses
        files = []
        completed = 0
        failed = 0
        for link in batch.assets:
            asset_q = select(Asset).where(Asset.id == link.asset_id)
            asset = (await self.db.execute(asset_q)).scalar_one_or_none()
            parse_status = asset.parse_status if asset else "unknown"
            files.append({
                "asset_id": link.asset_id,
                "original_filename": link.original_filename,
                "parse_status": parse_status,
            })
            if parse_status in ("parsed", "unsupported"):
                completed += 1
            elif parse_status == "failed":
                failed += 1

        # Derive batch status
        status = batch.status
        if batch.status in ("pending", "processing"):
            if completed + failed == batch.total_files:
                status = "completed" if failed == 0 else "partial_failed"

        return {
            "batch_id": batch.id,
            "status": status,
            "total_files": batch.total_files,
            "completed_files": completed,
            "failed_files": failed,
            "created_at": batch.created_at,
            "files": files,
        }
