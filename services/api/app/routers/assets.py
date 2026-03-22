"""Assets router: upload, list, get endpoints with tenant isolation."""

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_schemas.asset import AssetOut, ImportUrlRequest
from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta

from app.deps import get_current_user, get_db, get_settings_dep, get_tenant_id, require_role
from app.services.asset_service import AssetService
from app.services.audit_service import AuditService
from app.utils.storage import StorageClient
from shared_models import User

router = APIRouter(prefix="/v1/assets", tags=["assets"])

_RESP_AUTH = {
    401: {"description": "Unauthorized", "model": ErrorDetail},
    403: {"description": "Forbidden", "model": ErrorDetail},
}

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


@router.post(
    "/upload",
    response_model=DataResponse[AssetOut],
    status_code=201,
    summary="Upload a file asset",
    description="Uploads a file to the project's asset store (MinIO/S3). Requires editor role. File size is limited by MAX_UPLOAD_SIZE_MB.",
    responses={
        201: {"description": "Asset uploaded and metadata created"},
        **_RESP_AUTH,
        413: {"description": "File exceeds maximum upload size"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def upload_asset(
    project_id: uuid.UUID = Form(...),
    asset_type: str = Form(default="document"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = require_role("editor"),
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
    # Read file content — for files under max_upload_size_mb this is acceptable.
    # TODO(T-41-07): For very large files, consider streaming to MinIO directly.
    file_content = await file.read()
    asset = await svc.upload(
        project_id=project_id,
        filename=file.filename or "unknown",
        asset_type=asset_type,
        file_content=file_content,
        content_type=file.content_type or "application/octet-stream",
    )
    audit = AuditService(db, tenant_id, current_user.id)
    await audit.log("upload", "asset", asset.id, project_id=project_id)
    return DataResponse(data=AssetOut.model_validate(asset))


@router.post(
    "/import-url",
    response_model=DataResponse[AssetOut],
    status_code=201,
    summary="Import asset from URL",
    description="Downloads content from a URL and creates an asset record. Requires editor role.",
    responses={
        201: {"description": "Asset imported from URL"},
        **_RESP_AUTH,
        422: {"description": "Validation error — invalid URL format"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def import_url(
    body: ImportUrlRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = require_role("editor"),
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
    audit = AuditService(db, tenant_id, current_user.id)
    await audit.log("import_url", "asset", asset.id, project_id=body.project_id)
    return DataResponse(data=AssetOut.model_validate(asset))


@router.post(
    "/import-archive",
    status_code=201,
    summary="Import assets from archive",
    description="Extracts a ZIP archive and creates individual asset records for each file. Requires editor role.",
    responses={
        201: {"description": "Archive imported, assets created"},
        **_RESP_AUTH,
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def import_archive(
    project_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = require_role("editor"),
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
    audit = AuditService(db, tenant_id, current_user.id)
    await audit.log("import_archive", "asset", project_id, project_id=project_id)
    return DataResponse(data=result)


@router.get(
    "",
    response_model=ListResponse[AssetOut],
    summary="List assets",
    description="Returns a paginated list of assets for a given project.",
    responses={
        200: {"description": "Asset list returned"},
        **_RESP_AUTH,
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
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


@router.get(
    "/{asset_id}",
    response_model=DataResponse[AssetOut],
    summary="Get an asset",
    description="Returns metadata of a single asset by ID.",
    responses={
        200: {"description": "Asset details returned"},
        **_RESP_AUTH,
        404: {"description": "Asset not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def get_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    svc = AssetService(db, tenant_id, current_user.id)
    asset = await svc.get(asset_id)
    return DataResponse(data=AssetOut.model_validate(asset))
