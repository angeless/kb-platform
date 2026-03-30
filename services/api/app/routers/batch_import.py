"""Batch import router: ZIP upload and status query."""

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_schemas.batch_import import BatchImportCreatedOut, BatchImportOut
from shared_schemas.common import DataResponse, ErrorDetail

from app.deps import get_db, get_settings_dep, get_tenant_id, require_role
from app.services.batch_import_service import BatchImportService
from app.utils.storage import StorageClient
from shared_models import User

router = APIRouter(prefix="/v1/projects", tags=["batch-import"])

_RESP_AUTH = {
    401: {"description": "Unauthorized", "model": ErrorDetail},
    403: {"description": "Forbidden", "model": ErrorDetail},
}

# Reuse storage singleton from assets router
_storage_client: StorageClient | None = None


def get_storage(settings: Settings = Depends(get_settings_dep)) -> StorageClient | None:
    global _storage_client
    if _storage_client is None:
        try:
            _storage_client = StorageClient(settings)
            _storage_client.ensure_bucket()
        except Exception:
            return None
    return _storage_client


@router.post(
    "/{project_id}/batch-import",
    response_model=DataResponse[BatchImportCreatedOut],
    status_code=201,
    summary="Batch import from ZIP",
    description="Uploads a ZIP file, extracts supported files, creates asset records, and optionally starts ingestion.",
    responses={
        201: {"description": "Batch created"},
        **_RESP_AUTH,
        400: {"description": "Invalid file or empty archive", "model": ErrorDetail},
    },
)
async def create_batch_import(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    auto_start: bool = Form(default=True),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user: User = Depends(require_role("editor")),
    storage: StorageClient | None = Depends(get_storage),
):
    content = await file.read()
    svc = BatchImportService(db, tenant_id, user.id, storage)
    result = await svc.create_batch(
        project_id, content, file.filename or "upload.zip", auto_start
    )
    await db.commit()
    return DataResponse(data=BatchImportCreatedOut(**result))


@router.get(
    "/{project_id}/batch-import/{batch_id}",
    response_model=DataResponse[BatchImportOut],
    summary="Get batch import status",
    description="Returns batch import status with per-file parse status.",
    responses={
        200: {"description": "Batch status returned"},
        **_RESP_AUTH,
        404: {"description": "Batch not found", "model": ErrorDetail},
    },
)
async def get_batch_import(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = BatchImportService(db, tenant_id, uuid.UUID(int=0), None)
    result = await svc.get_batch(batch_id)
    return DataResponse(data=BatchImportOut(**result))
