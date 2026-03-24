"""Cross-reference router: CRUD + auto-suggest for document links."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta
from shared_schemas.cross_reference import AutoSuggestRequest, CrossRefCreate, CrossRefOut

from app.deps import get_db, get_tenant_id, require_role
from shared_models import User
from app.services.cross_ref_service import CrossRefService

router = APIRouter(prefix="/v1/cross-refs", tags=["cross-references"])

_RESP_AUTH = {
    401: {"description": "Unauthorized", "model": ErrorDetail},
    403: {"description": "Forbidden", "model": ErrorDetail},
}


@router.post(
    "",
    response_model=DataResponse[CrossRefOut],
    summary="Create a cross-reference between two documents",
    responses={200: {"description": "Cross-reference created"}, **_RESP_AUTH},
)
async def create_cross_ref(
    body: CrossRefCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user: User = Depends(require_role("editor")),
):
    svc = CrossRefService(db, tenant_id)
    ref = await svc.create(
        source_doc_id=uuid.UUID(body.source_doc_id),
        target_doc_id=uuid.UUID(body.target_doc_id),
        relation_type=body.relation_type,
        confidence=body.confidence,
        note=body.note,
        created_by="user",
    )
    await db.commit()
    return DataResponse(data=CrossRefOut.model_validate(ref))


@router.get(
    "/doc/{doc_id}",
    response_model=ListResponse[CrossRefOut],
    summary="Get all cross-references for a document",
    responses={200: {"description": "Cross-references returned"}, **_RESP_AUTH},
)
async def get_doc_cross_refs(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = CrossRefService(db, tenant_id)
    refs = await svc.list_for_doc(doc_id)
    return ListResponse(
        data=[CrossRefOut(**r) for r in refs],
        meta=PaginationMeta(page=1, page_size=len(refs), total=len(refs)),
    )


@router.delete(
    "/{ref_id}",
    response_model=DataResponse[dict],
    summary="Delete a cross-reference",
    responses={200: {"description": "Cross-reference deleted"}, **_RESP_AUTH},
)
async def delete_cross_ref(
    ref_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user: User = Depends(require_role("editor")),
):
    svc = CrossRefService(db, tenant_id)
    deleted = await svc.delete(ref_id)
    await db.commit()
    return DataResponse(data={"deleted": deleted})


@router.post(
    "/auto-suggest",
    response_model=ListResponse[dict],
    summary="Auto-suggest cross-references for a document",
    responses={200: {"description": "Suggestions returned"}, **_RESP_AUTH},
)
async def auto_suggest_cross_refs(
    body: AutoSuggestRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = CrossRefService(db, tenant_id)
    suggestions = await svc.auto_suggest(uuid.UUID(body.doc_id), body.max_results)
    return ListResponse(
        data=suggestions,
        meta=PaginationMeta(page=1, page_size=len(suggestions), total=len(suggestions)),
    )
