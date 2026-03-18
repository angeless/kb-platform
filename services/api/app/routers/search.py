"""Search router: full-text search endpoint."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import ListResponse, PaginationMeta
from shared_schemas.search import SearchHit, TextSearchRequest

from app.deps import get_db, get_tenant_id
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
