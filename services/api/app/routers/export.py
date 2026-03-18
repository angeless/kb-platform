"""Export router: download documents as Markdown or ZIP."""

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_tenant_id
from app.services.export_service import ExportService

router = APIRouter(tags=["export"])


@router.get("/v1/docs/{doc_id}/export")
async def export_single_doc(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ExportService(db, tenant_id)
    filename, content = await svc.export_single_doc(doc_id)
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/v1/projects/{project_id}/export")
async def export_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ExportService(db, tenant_id)
    zip_filename, zip_bytes = await svc.export_project_zip(project_id)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )
