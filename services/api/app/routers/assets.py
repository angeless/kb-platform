"""Assets router: upload, list, get endpoints with tenant isolation."""

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_schemas.asset import AssetOut, ImportUrlRequest
from shared_schemas.common import DataResponse, ListResponse, PaginationMeta

from app.deps import get_current_user, get_db, get_settings_dep, get_tenant_id
from app.services.asset_service import AssetService
from app.utils.storage import StorageClient
from shared_models import User

router = APIRouter(prefix="/v1/assets", tags=["assets"])

# Lazy-initialized storage client (None in test, real in production)
_storage_client: StorageClient | None = None


def get_storage(settings: Settings = Depends(get_settings_dep)) -> StorageClient | None:
    """Get or create the StorageClient singleton. Returns None if S3 is unreachable."""
    global _storage_client
    if _storage_client is None:
        try:
            _storage_client = StorageClient(settings)
            _storage_client.ensure_bucket()
        except Exception:
            return None
    return _storage_client


@router.post("/upload", response_model=DataResponse[AssetOut], status_code=201)
async def upload_asset(
    project_id: uuid.UUID = Form(...),
    asset_type: str = Form(default="document"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings_dep),
    storage: StorageClient | None = Depends(get_storage),
):
    svc = AssetService(
        db,
        tenant_id,
        current_user.id,
        storage=storage,
        max_upload_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
    )
    file_content = await file.read()
    asset = await svc.upload(
        project_id=project_id,
        filename=file.filename or "unknown",
        asset_type=asset_type,
        file_content=file_content,
        content_type=file.content_type or "application/octet-stream",
    )
    return DataResponse(data=AssetOut.model_validate(asset))


@router.post("/import-url", response_model=DataResponse[AssetOut], status_code=201)
async def import_url(
    body: ImportUrlRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings_dep),
    storage: StorageClient | None = Depends(get_storage),
):
    svc = AssetService(
        db,
        tenant_id,
        current_user.id,
        storage=storage,
        max_upload_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
    )
    asset = await svc.import_url(body.project_id, str(body.url))
    return DataResponse(data=AssetOut.model_validate(asset))


@router.post("/import-archive", status_code=201)
async def import_archive(
    project_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings_dep),
    storage: StorageClient | None = Depends(get_storage),
):
    svc = AssetService(
        db,
        tenant_id,
        current_user.id,
        storage=storage,
        max_upload_size_bytes=settings.max_upload_size_mb * 1024 * 1024,
    )
    archive_content = await file.read()
    result = await svc.import_archive(project_id, archive_content, file.filename or "archive.zip")
    return DataResponse(data=result)


@router.get("", response_model=ListResponse[AssetOut])
async def list_assets(
    project_id: uuid.UUID = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    svc = AssetService(db, tenant_id, current_user.id)
    assets, total = await svc.list(project_id=project_id, page=page, page_size=page_size)
    return ListResponse(
        data=[AssetOut.model_validate(a) for a in assets],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/{asset_id}", response_model=DataResponse[AssetOut])
async def get_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    svc = AssetService(db, tenant_id, current_user.id)
    asset = await svc.get(asset_id)
    return DataResponse(data=AssetOut.model_validate(asset))
