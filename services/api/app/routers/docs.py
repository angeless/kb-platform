"""Knowledge docs router: list, get, review, publish."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta
from shared_schemas.knowledge import AssignNodeRequest, BatchDocRequest, BatchFailedItem, BatchResultOut, DocRejectRequest, DocUpdateContent, DocVersionOut, KnowledgeDocDetailOut, KnowledgeDocOut, VersionDiffOut

from app.deps import get_current_user, get_db, get_tenant_id, require_role
from app.services.audit_service import AuditService
from app.services.doc_service import DocService
from shared_models import User

router = APIRouter(prefix="/v1/docs", tags=["docs"])

_RESP_AUTH = {
    401: {"description": "Unauthorized", "model": ErrorDetail},
    403: {"description": "Forbidden", "model": ErrorDetail},
}


@router.get(
    "",
    response_model=ListResponse[KnowledgeDocOut],
    summary="List knowledge documents",
    description="Returns a paginated list of knowledge documents for a given project.",
    responses={
        200: {"description": "Document list returned"},
        **_RESP_AUTH,
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
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


@router.get(
    "/pending",
    response_model=ListResponse[KnowledgeDocOut],
    summary="List pending documents",
    description="Returns a paginated list of documents awaiting review for a given project.",
    responses={
        200: {"description": "Pending document list returned"},
        **_RESP_AUTH,
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def list_pending_docs(
    project_id: uuid.UUID = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = DocService(db, tenant_id)
    docs, total = await svc.list_pending(project_id=project_id, page=page, page_size=page_size)
    return ListResponse(
        data=[KnowledgeDocOut.model_validate(d) for d in docs],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )


# --- Batch operations (must be before /{doc_id} routes) ---


@router.post(
    "/batch/review",
    response_model=DataResponse[BatchResultOut],
    summary="Batch review documents",
    description="Transitions multiple documents to 'reviewed' status. Requires reviewer role. Returns succeeded and failed IDs.",
    responses={
        200: {"description": "Batch review result"},
        **_RESP_AUTH,
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def batch_review(
    body: BatchDocRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = require_role("reviewer"),
):
    svc = DocService(db, tenant_id)
    audit = AuditService(db, tenant_id, current_user.id)
    succeeded, failed = [], []
    for doc_id in body.doc_ids:
        try:
            doc = await svc.review(doc_id)
            await audit.log("review", "knowledge_doc", doc_id, project_id=doc.project_id)
            succeeded.append(doc_id)
        except Exception as e:
            error_code = getattr(e, "error_code", "OPERATION_FAILED")
            failed.append(BatchFailedItem(id=doc_id, error_code=str(error_code), message=str(e)))
    return DataResponse(data=BatchResultOut(succeeded=succeeded, failed=failed))


@router.post(
    "/batch/publish",
    response_model=DataResponse[BatchResultOut],
    summary="Batch publish documents",
    description="Transitions multiple reviewed documents to 'published' status. Requires project_admin role.",
    responses={
        200: {"description": "Batch publish result"},
        **_RESP_AUTH,
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def batch_publish(
    body: BatchDocRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = require_role("project_admin"),
):
    svc = DocService(db, tenant_id)
    audit = AuditService(db, tenant_id, current_user.id)
    succeeded, failed = [], []
    for doc_id in body.doc_ids:
        try:
            doc = await svc.publish(doc_id)
            await audit.log("publish", "knowledge_doc", doc_id, project_id=doc.project_id)
            succeeded.append(doc_id)
        except Exception as e:
            error_code = getattr(e, "error_code", "OPERATION_FAILED")
            failed.append(BatchFailedItem(id=doc_id, error_code=str(error_code), message=str(e)))
    return DataResponse(data=BatchResultOut(succeeded=succeeded, failed=failed))


@router.post(
    "/batch/reject",
    response_model=DataResponse[BatchResultOut],
    summary="Batch reject documents",
    description="Rejects multiple documents, returning them to draft status. Requires reviewer role.",
    responses={
        200: {"description": "Batch reject result"},
        **_RESP_AUTH,
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def batch_reject(
    body: BatchDocRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = require_role("reviewer"),
):
    svc = DocService(db, tenant_id)
    audit = AuditService(db, tenant_id, current_user.id)
    succeeded, failed = [], []
    for doc_id in body.doc_ids:
        try:
            doc = await svc.reject(doc_id)
            await audit.log("reject", "knowledge_doc", doc_id, project_id=doc.project_id)
            succeeded.append(doc_id)
        except Exception as e:
            error_code = getattr(e, "error_code", "OPERATION_FAILED")
            failed.append(BatchFailedItem(id=doc_id, error_code=str(error_code), message=str(e)))
    return DataResponse(data=BatchResultOut(succeeded=succeeded, failed=failed))


# --- Single doc operations ---


@router.get(
    "/{doc_id}",
    response_model=DataResponse[KnowledgeDocDetailOut],
    summary="Get document details",
    description="Returns full details of a knowledge document including content, metadata, and version history.",
    responses={
        200: {"description": "Document details returned"},
        **_RESP_AUTH,
        404: {"description": "Document not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def get_doc(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = DocService(db, tenant_id)
    doc = await svc.get(doc_id)
    return DataResponse(data=KnowledgeDocDetailOut.model_validate(doc))


@router.get(
    "/{doc_id}/versions/{version}",
    response_model=DataResponse[DocVersionOut],
    summary="Get document version",
    description="Returns a specific historical version of a document by version number.",
    responses={
        200: {"description": "Version details returned"},
        **_RESP_AUTH,
        404: {"description": "Document or version not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def get_doc_version(
    doc_id: uuid.UUID,
    version: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = DocService(db, tenant_id)
    ver = await svc.get_version(doc_id, version)
    return DataResponse(data=DocVersionOut.model_validate(ver))


@router.get(
    "/{doc_id}/diff",
    response_model=DataResponse[VersionDiffOut],
    summary="Compare document versions",
    description="Returns a diff between two versions of a document, showing added, removed, and changed content.",
    responses={
        200: {"description": "Version diff returned"},
        **_RESP_AUTH,
        404: {"description": "Document or version not found", "model": ErrorDetail},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def diff_versions(
    doc_id: uuid.UUID,
    from_version: int = Query(..., ge=1),
    to_version: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = DocService(db, tenant_id)
    result = await svc.diff_versions(doc_id, from_version, to_version)
    return DataResponse(data=VersionDiffOut(**result))


@router.post(
    "/{doc_id}/assign-node",
    response_model=DataResponse[KnowledgeDocOut],
    summary="Assign document to architecture node",
    description="Links a knowledge document to an architecture tree node. Requires editor role.",
    responses={
        200: {"description": "Document assigned to node"},
        **_RESP_AUTH,
        404: {"description": "Document or node not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def assign_node(
    doc_id: uuid.UUID,
    body: AssignNodeRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = require_role("editor"),
):
    svc = DocService(db, tenant_id)
    doc = await svc.assign_node(doc_id, body.node_id)
    audit = AuditService(db, tenant_id, current_user.id)
    await audit.log("assign_node", "knowledge_doc", doc_id, project_id=doc.project_id)
    return DataResponse(data=KnowledgeDocOut.model_validate(doc))


@router.post(
    "/{doc_id}/review",
    response_model=DataResponse[KnowledgeDocOut],
    summary="Review a document",
    description="Transitions a document from draft to reviewed status. Requires reviewer role.",
    responses={
        200: {"description": "Document reviewed"},
        **_RESP_AUTH,
        404: {"description": "Document not found", "model": ErrorDetail},
        409: {"description": "Invalid state transition", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def review_doc(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = require_role("reviewer"),
):
    svc = DocService(db, tenant_id)
    doc = await svc.review(doc_id)
    audit = AuditService(db, tenant_id, current_user.id)
    await audit.log("review", "knowledge_doc", doc_id, project_id=doc.project_id)
    return DataResponse(data=KnowledgeDocOut.model_validate(doc))


@router.post(
    "/{doc_id}/publish",
    response_model=DataResponse[KnowledgeDocOut],
    summary="Publish a document",
    description="Transitions a reviewed document to published status. Requires project_admin role.",
    responses={
        200: {"description": "Document published"},
        **_RESP_AUTH,
        404: {"description": "Document not found", "model": ErrorDetail},
        409: {"description": "Invalid state transition", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def publish_doc(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = require_role("project_admin"),
):
    svc = DocService(db, tenant_id)
    doc = await svc.publish(doc_id)
    audit = AuditService(db, tenant_id, current_user.id)
    await audit.log("publish", "knowledge_doc", doc_id, project_id=doc.project_id)
    return DataResponse(data=KnowledgeDocOut.model_validate(doc))


@router.put(
    "/{doc_id}/content",
    response_model=DataResponse[KnowledgeDocOut],
    summary="Update document content",
    description="Replaces the content of a document and creates a new version. Requires editor role.",
    responses={
        200: {"description": "Document content updated, new version created"},
        **_RESP_AUTH,
        404: {"description": "Document not found", "model": ErrorDetail},
        409: {"description": "Document is not in editable state", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def update_doc_content(
    doc_id: uuid.UUID,
    body: DocUpdateContent,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = require_role("editor"),
):
    svc = DocService(db, tenant_id)
    doc = await svc.update_content(doc_id, body.content_md, body.change_reason, current_user.id)
    audit = AuditService(db, tenant_id, current_user.id)
    await audit.log("edit", "knowledge_doc", doc_id, project_id=doc.project_id)
    return DataResponse(data=KnowledgeDocOut.model_validate(doc))


@router.post(
    "/{doc_id}/reject",
    response_model=DataResponse[KnowledgeDocOut],
    summary="Reject a document",
    description="Rejects a document with a reason, returning it to draft status. Requires reviewer role.",
    responses={
        200: {"description": "Document rejected"},
        **_RESP_AUTH,
        404: {"description": "Document not found", "model": ErrorDetail},
        409: {"description": "Invalid state transition", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def reject_doc(
    doc_id: uuid.UUID,
    body: DocRejectRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = require_role("reviewer"),
):
    svc = DocService(db, tenant_id)
    doc = await svc.reject(doc_id)
    audit = AuditService(db, tenant_id, current_user.id)
    await audit.log("reject", "knowledge_doc", doc_id, project_id=doc.project_id, detail={"reason": body.reject_reason})
    return DataResponse(data=KnowledgeDocOut.model_validate(doc))
