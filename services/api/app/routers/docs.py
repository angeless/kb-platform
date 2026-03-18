"""Knowledge docs router: list, get, review, publish."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ListResponse, PaginationMeta
from shared_schemas.knowledge import DocVersionOut, KnowledgeDocOut

from app.deps import get_db, get_tenant_id
from app.services.doc_service import DocService

router = APIRouter(prefix="/v1/docs", tags=["docs"])


@router.get("", response_model=ListResponse[KnowledgeDocOut])
async def list_docs(
    project_id: uuid.UUID = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = DocService(db, tenant_id)
    docs, total = await svc.list(project_id=project_id, page=page, page_size=page_size)
    return ListResponse(
        data=[KnowledgeDocOut.model_validate(d) for d in docs],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/{doc_id}", response_model=DataResponse[KnowledgeDocOut])
async def get_doc(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = DocService(db, tenant_id)
    doc = await svc.get(doc_id)
    return DataResponse(data=KnowledgeDocOut.model_validate(doc))


@router.post("/{doc_id}/review", response_model=DataResponse[KnowledgeDocOut])
async def review_doc(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = DocService(db, tenant_id)
    doc = await svc.review(doc_id)
    return DataResponse(data=KnowledgeDocOut.model_validate(doc))


@router.post("/{doc_id}/publish", response_model=DataResponse[KnowledgeDocOut])
async def publish_doc(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = DocService(db, tenant_id)
    doc = await svc.publish(doc_id)
    return DataResponse(data=KnowledgeDocOut.model_validate(doc))
