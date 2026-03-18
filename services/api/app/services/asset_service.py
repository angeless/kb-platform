"""Asset service: upload, list, get with tenant isolation."""

import hashlib
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import AppException, ConflictException, ErrorCode, NotFoundException
from shared_models import Asset, Project

from app.utils.storage import StorageClient, is_allowed_file


class AssetService:
    """Operations for assets, scoped to a single tenant via project ownership."""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        storage: StorageClient | None = None,
        max_upload_size_bytes: int = 100 * 1024 * 1024,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.storage = storage
        self.max_upload_size_bytes = max_upload_size_bytes

    async def _verify_project(self, project_id: uuid.UUID) -> Project:
        """Verify project exists and belongs to tenant."""
        q = select(Project).where(
            Project.id == project_id,
            Project.tenant_id == self.tenant_id,
            Project.status != "deleted",
        )
        result = await self.db.execute(q)
        project = result.scalar_one_or_none()
        if project is None:
            raise NotFoundException(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                message="Project not found",
            )
        return project

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
                message="Duplicate file already uploaded",
            )

        asset_id = uuid.uuid4()
        object_path = f"{self.tenant_id}/{project_id}/{asset_id}/{filename}"

        # Upload to MinIO/S3 if storage client is available
        if self.storage is not None:
            self.storage.upload_file(object_path, file_content, content_type)

        asset = Asset(
            id=asset_id,
            project_id=project_id,
            asset_type=asset_type,
            filename=filename,
            object_path=object_path,
            file_hash=file_hash,
            file_size=len(file_content),
            parse_status="pending",
            uploaded_by=self.user_id,
        )
        self.db.add(asset)
        await self.db.flush()
        return asset

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
                message="Asset not found",
            )
        await self._verify_project(asset.project_id)
        return asset
