"""Review workflow router: create, assign, approve, reject, resubmit, list."""

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta

from app.deps import get_current_user, get_db, get_kb_id, require_role
from app.services.audit_service import AuditService
from app.services.review_service import ReviewService
from shared_models import User

router = APIRouter(prefix="/v1/projects/{project_id}/reviews", tags=["reviews"])

_RESP_AUTH = {
    401: {"description": "Unauthorized", "model": ErrorDetail},
    403: {"description": "Forbidden", "model": ErrorDetail},
}


# --- Request schemas ---

class CreateReviewRequest(BaseModel):
    doc_id: uuid.UUID


class AssignReviewerRequest(BaseModel):
    reviewer_id: uuid.UUID


class ReviewNoteRequest(BaseModel):
    note: str = ""


# --- Response schema ---

class ReviewTaskOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    doc_id: uuid.UUID
    reviewer_id: uuid.UUID | None
    status: str
    assigned_at: str | None
    reviewed_at: str | None
    review_note: str | None
    created_by: uuid.UUID
    created_at: str

    model_config = {"from_attributes": True}


def _to_out(task) -> ReviewTaskOut:
    return ReviewTaskOut(
        id=task.id,
        project_id=task.project_id,
        doc_id=task.doc_id,
        reviewer_id=task.reviewer_id,
        status=task.status,
        assigned_at=task.assigned_at.isoformat() if task.assigned_at else None,
        reviewed_at=task.reviewed_at.isoformat() if task.reviewed_at else None,
        review_note=task.review_note,
        created_by=task.created_by,
        created_at=task.created_at.isoformat() if task.created_at else "",
    )


# --- Endpoints ---

@router.post(
    "",
    response_model=DataResponse[ReviewTaskOut],
    status_code=201,
    summary="Create review task",
    responses={**_RESP_AUTH, 400: {"model": ErrorDetail}},
)
async def create_review(
    project_id: uuid.UUID,
    body: CreateReviewRequest,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    user: User = require_role("editor"),
):
    svc = ReviewService(db, kb_id)
    task = await svc.create(project_id, body.doc_id, user.id)
    await AuditService(db, kb_id, user.id).log("review_create", "review_task", str(task.id))
    await db.commit()
    return DataResponse(data=_to_out(task))


@router.post(
    "/{review_id}/assign",
    response_model=DataResponse[ReviewTaskOut],
    summary="Assign reviewer",
    responses={**_RESP_AUTH, 400: {"model": ErrorDetail}},
)
async def assign_reviewer(
    project_id: uuid.UUID,
    review_id: uuid.UUID,
    body: AssignReviewerRequest,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    user: User = require_role("project_admin"),
):
    svc = ReviewService(db, kb_id)
    task = await svc.assign(project_id, review_id, body.reviewer_id)
    await AuditService(db, kb_id, user.id).log("review_assign", "review_task", str(task.id))
    await db.commit()
    return DataResponse(data=_to_out(task))


@router.post(
    "/{review_id}/approve",
    response_model=DataResponse[ReviewTaskOut],
    summary="Approve review",
    responses={**_RESP_AUTH, 400: {"model": ErrorDetail}, 403: {"model": ErrorDetail}},
)
async def approve_review(
    project_id: uuid.UUID,
    review_id: uuid.UUID,
    body: ReviewNoteRequest = ReviewNoteRequest(),
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    user: User = Depends(get_current_user),
):
    svc = ReviewService(db, kb_id)
    task = await svc.approve(project_id, review_id, user.id, body.note or None)
    await AuditService(db, kb_id, user.id).log("review_approve", "review_task", str(task.id))
    await db.commit()
    return DataResponse(data=_to_out(task))


@router.post(
    "/{review_id}/reject",
    response_model=DataResponse[ReviewTaskOut],
    summary="Reject review",
    responses={**_RESP_AUTH, 400: {"model": ErrorDetail}, 403: {"model": ErrorDetail}},
)
async def reject_review(
    project_id: uuid.UUID,
    review_id: uuid.UUID,
    body: ReviewNoteRequest,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    user: User = Depends(get_current_user),
):
    svc = ReviewService(db, kb_id)
    task = await svc.reject(project_id, review_id, user.id, body.note)
    await AuditService(db, kb_id, user.id).log("review_reject", "review_task", str(task.id))
    await db.commit()
    return DataResponse(data=_to_out(task))


@router.post(
    "/{review_id}/resubmit",
    response_model=DataResponse[ReviewTaskOut],
    summary="Resubmit rejected review",
    responses={**_RESP_AUTH, 400: {"model": ErrorDetail}, 403: {"model": ErrorDetail}},
)
async def resubmit_review(
    project_id: uuid.UUID,
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    user: User = Depends(get_current_user),
):
    svc = ReviewService(db, kb_id)
    task = await svc.resubmit(project_id, review_id, user.id)
    await AuditService(db, kb_id, user.id).log("review_resubmit", "review_task", str(task.id))
    await db.commit()
    return DataResponse(data=_to_out(task))


@router.get(
    "",
    response_model=ListResponse[ReviewTaskOut],
    summary="List review tasks",
    responses={**_RESP_AUTH},
)
async def list_reviews(
    project_id: uuid.UUID,
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = Depends(get_current_user),
):
    svc = ReviewService(db, kb_id)
    tasks, total = await svc.list_reviews(project_id, status=status, page=page, page_size=page_size)
    return ListResponse(
        data=[_to_out(t) for t in tasks],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )
