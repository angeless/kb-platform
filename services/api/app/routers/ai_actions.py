"""AI actions router: generate summary, suggest tags for knowledge docs."""

import logging
import uuid

from fastapi import APIRouter, Depends, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ErrorDetail
from shared_errors import AppException, ErrorCode, NotFoundException
from shared_models import KnowledgeDoc, User

from app.deps import get_db, get_kb_id, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/docs", tags=["ai-actions"])

_RESP_AUTH = {
    401: {"description": "Unauthorized", "model": ErrorDetail},
    403: {"description": "Forbidden", "model": ErrorDetail},
}

# Celery task dispatch — lazy import to avoid hard dependency
_celery_app = None


def _get_celery_app():
    global _celery_app
    if _celery_app is None:
        try:
            from celery import Celery
            from shared_config.settings import get_settings
            settings = get_settings()
            _celery_app = Celery(broker=settings.redis_url)
        except Exception:
            logger.warning("Celery not available, AI tasks will not be dispatched")
    return _celery_app


@router.post(
    "/{doc_id}/ai-summarize",
    response_model=DataResponse[dict],
    summary="Generate AI summary for a document",
    description="Calls the AI orchestrator to generate a summary for the specified knowledge document. "
                "The summary is written to the doc's summary field and returned.",
    responses={
        200: {"description": "Summary generated"},
        404: {"description": "Document not found", "model": ErrorDetail},
        **_RESP_AUTH,
        500: {"description": "AI generation failed", "model": ErrorDetail},
    },
)
async def ai_summarize(
    doc_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    current_user: User = require_role("editor"),
):
    doc = (await db.execute(
        select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
    )).scalar_one_or_none()

    if doc is None:
        raise NotFoundException(ErrorCode.DOC_NOT_FOUND, "文档不存在", detail={"doc_id": str(doc_id)})

    celery = _get_celery_app()
    if celery is None:
        raise AppException(ErrorCode.SYSTEM_INTERNAL_ERROR, "AI 服务不可用", status_code=500)

    result = celery.send_task(
        "orchestrator.generate_summary",
        args=[str(doc_id)],
    )

    try:
        task_result = result.get(timeout=60)
    except Exception as e:
        logger.error("AI summarize task failed for doc %s: %s", doc_id, e)
        raise AppException(ErrorCode.SYSTEM_INTERNAL_ERROR, "AI 摘要生成失败", status_code=500)

    if task_result.get("status") == "error":
        raise AppException(
            ErrorCode.SYSTEM_INTERNAL_ERROR,
            task_result.get("message", "AI 摘要生成失败"),
            status_code=500,
        )

    return DataResponse(data={"summary": task_result.get("summary", "")})


@router.post(
    "/{doc_id}/ai-suggest-tags",
    response_model=DataResponse[dict],
    summary="Suggest AI-generated keyword tags for a document",
    description="Calls the AI orchestrator to suggest keyword tags for the specified knowledge document. "
                "The keywords are written to the doc's keywords field and returned.",
    responses={
        200: {"description": "Tags suggested"},
        404: {"description": "Document not found", "model": ErrorDetail},
        **_RESP_AUTH,
        500: {"description": "AI generation failed", "model": ErrorDetail},
    },
)
async def ai_suggest_tags(
    doc_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    current_user: User = require_role("editor"),
):
    doc = (await db.execute(
        select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
    )).scalar_one_or_none()

    if doc is None:
        raise NotFoundException(ErrorCode.DOC_NOT_FOUND, "文档不存在", detail={"doc_id": str(doc_id)})

    celery = _get_celery_app()
    if celery is None:
        raise AppException(ErrorCode.SYSTEM_INTERNAL_ERROR, "AI 服务不可用", status_code=500)

    result = celery.send_task(
        "orchestrator.suggest_tags",
        args=[str(doc_id)],
    )

    try:
        task_result = result.get(timeout=60)
    except Exception as e:
        logger.error("AI suggest-tags task failed for doc %s: %s", doc_id, e)
        raise AppException(ErrorCode.SYSTEM_INTERNAL_ERROR, "AI 标签推荐失败", status_code=500)

    if task_result.get("status") == "error":
        raise AppException(
            ErrorCode.SYSTEM_INTERNAL_ERROR,
            task_result.get("message", "AI 标签推荐失败"),
            status_code=500,
        )

    return DataResponse(data={"keywords": task_result.get("keywords", [])})
