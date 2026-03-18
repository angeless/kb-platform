"""Asset service: upload, list, get with tenant isolation."""

import hashlib
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ConflictException, ErrorCode, NotFoundException
from shared_models import Asset, Project


class AssetService:
    """Operations for assets, scoped to a single tenant via project ownership."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

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
    ) -> Asset:
        """Upload a file asset. Compute SHA-256, check duplicate, create record."""
        await self._verify_project(project_id)

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

        asset = Asset(
            id=uuid.uuid4(),
            project_id=project_id,
            asset_type=asset_type,
            filename=filename,
            object_path=f"pending/{project_id}/{filename}",
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
