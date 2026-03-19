"""Search router: full-text and semantic search endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ListResponse, PaginationMeta
from shared_schemas.search import SearchHit, SemanticHit, SemanticSearchRequest, TextSearchRequest

from app.deps import get_db, get_tenant_id
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SearchService

router = APIRouter(prefix="/v1/search", tags=["search"])


@router.post("/text", response_model=ListResponse[SearchHit])
async def text_search(
    body: TextSearchRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = SearchService(db, tenant_id)
    results, total = await svc.text_search(
        project_id=body.project_id,
        query=body.query,
        page=body.page,
        page_size=body.page_size,
    )
    return ListResponse(
        data=[SearchHit(**r) for r in results],
        meta=PaginationMeta(
            page=body.page,
            page_size=body.page_size,
            total=total,
        ),
    )


@router.post("/semantic", response_model=DataResponse[list[SemanticHit]])
async def semantic_search(
    body: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = EmbeddingService(db, tenant_id)
    results = await svc.semantic_search(
        project_id=body.project_id,
        query=body.query,
        top_k=body.top_k,
    )
    return DataResponse(data=[SemanticHit(**r) for r in results])


@router.post("/embed/{doc_id}", response_model=DataResponse)
async def embed_doc(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = EmbeddingService(db, tenant_id)
    record = await svc.embed_doc(doc_id)
    return DataResponse(data={
        "doc_id": str(record.doc_id),
        "dimensions": record.dimensions,
        "model_name": record.model_name,
    })
