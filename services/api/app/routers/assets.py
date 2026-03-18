"""Assets router: upload, list, get endpoints with tenant isolation."""

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.asset import AssetOut
from shared_schemas.common import DataResponse, ListResponse, PaginationMeta

from app.deps import get_current_user, get_db, get_tenant_id
from app.services.asset_service import AssetService
from shared_models import User

router = APIRouter(prefix="/v1/assets", tags=["assets"])


@router.post("/upload", response_model=DataResponse[AssetOut], status_code=201)
async def upload_asset(
    project_id: uuid.UUID = Form(...),
    asset_type: str = Form(default="document"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    svc = AssetService(db, tenant_id, current_user.id)
    file_content = await file.read()
    asset = await svc.upload(
        project_id=project_id,
        filename=file.filename or "unknown",
        asset_type=asset_type,
        file_content=file_content,
    )
    return DataResponse(data=AssetOut.model_validate(asset))


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
