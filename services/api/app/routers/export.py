"""Export router: download documents as Markdown or ZIP."""

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import ErrorDetail

from app.deps import get_db, get_kb_id
from app.services.export_service import ExportService

router = APIRouter(tags=["export"])

_RESP_AUTH = {
    401: {"description": "Unauthorized", "model": ErrorDetail},
    403: {"description": "Forbidden", "model": ErrorDetail},
}


@router.get(
    "/v1/docs/{doc_id}/export",
    summary="Export a single document",
    description="Downloads a single knowledge document as a Markdown file.",
    responses={
        200: {"description": "Markdown file returned", "content": {"text/markdown": {}}},
        **_RESP_AUTH,
        404: {"description": "Document not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def export_single_doc(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
):
    svc = ExportService(db, kb_id)
    filename, content = await svc.export_single_doc(doc_id)
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/v1/projects/{project_id}/export",
    summary="Export all project documents",
    description="Downloads all published documents in a project as a ZIP archive containing individual Markdown files.",
    responses={
        200: {"description": "ZIP archive returned", "content": {"application/zip": {}}},
        **_RESP_AUTH,
        404: {"description": "Project not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def export_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
):
    svc = ExportService(db, kb_id)
    zip_filename, zip_bytes = await svc.export_project_zip(project_id)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )
