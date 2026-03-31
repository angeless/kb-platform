"""AI actions router: generate summary, suggest tags, detect contradictions."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ErrorDetail
from shared_errors import AppException, ErrorCode, NotFoundException
from shared_models import KnowledgeDoc, Project, User

from app.deps import get_db, get_kb_id, require_role

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai-actions"])

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
    "/v1/docs/{doc_id}/ai-summarize",
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

    return DataResponse(data={
        "summary": task_result.get("summary", ""),
        "confidence": task_result.get("confidence"),
    })


@router.post(
    "/v1/docs/{doc_id}/ai-suggest-tags",
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

    return DataResponse(data={
        "keywords": task_result.get("keywords", []),
        "confidence": task_result.get("confidence"),
    })


# ---------------------------------------------------------------------------
# Cross-document contradiction detection (v0.46.5)
# ---------------------------------------------------------------------------


class DetectContradictionsRequest(BaseModel):
    max_pairs: int = Field(default=50, ge=1, le=200)


@router.post(
    "/v1/projects/{project_id}/ai-detect-contradictions",
    response_model=DataResponse[dict],
    summary="Detect contradictions between documents in a project",
    description="Triggers AI to compare document pairs and detect factual contradictions. "
                "Results are automatically saved as 'contradicts' CrossReference records.",
    responses={
        200: {"description": "Detection completed"},
        **_RESP_AUTH,
        500: {"description": "AI detection failed", "model": ErrorDetail},
    },
)
async def ai_detect_contradictions(
    project_id: uuid.UUID = Path(...),
    body: Optional[DetectContradictionsRequest] = None,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    current_user: User = require_role("editor"),
):
    # Tenant isolation: verify project belongs to caller's tenant
    proj = (await db.execute(
        select(Project.id).where(Project.id == project_id, Project.kb_id == kb_id)
    )).scalar_one_or_none()
    if proj is None:
        raise NotFoundException(ErrorCode.PROJECT_NOT_FOUND, "Project not found")
    max_pairs = body.max_pairs if body else 50

    celery = _get_celery_app()
    if celery is None:
        raise AppException(ErrorCode.SYSTEM_INTERNAL_ERROR, "AI 服务不可用", status_code=500)

    result = celery.send_task(
        "orchestrator.detect_contradictions",
        args=[str(project_id)],
        kwargs={"max_pairs": max_pairs},
    )

    try:
        task_result = result.get(timeout=120)
    except Exception as e:
        logger.error("Contradiction detection failed for project %s: %s", project_id, e)
        raise AppException(ErrorCode.SYSTEM_INTERNAL_ERROR, "AI 矛盾检测失败", status_code=500)

    if task_result.get("status") == "error":
        raise AppException(
            ErrorCode.SYSTEM_INTERNAL_ERROR,
            task_result.get("message", "AI 矛盾检测失败"),
            status_code=500,
        )

    return DataResponse(data={
        "total_pairs_checked": task_result.get("total_pairs_checked", 0),
        "contradictions_found": task_result.get("contradictions_found", 0),
        "cross_refs_created": task_result.get("cross_refs_created", []),
    })


# ---------------------------------------------------------------------------
# Cross-document pattern discovery (v0.46.6)
# ---------------------------------------------------------------------------

@router.post(
    "/v1/projects/{project_id}/ai-discover-patterns",
    response_model=DataResponse[dict],
    summary="Discover cross-document patterns in a project",
    description="Analyzes all documents to find theme clusters, frequent associations, "
                "and knowledge gaps. Results are cached for 24h.",
    responses={
        200: {"description": "Pattern analysis completed"},
        **_RESP_AUTH,
        500: {"description": "AI analysis failed", "model": ErrorDetail},
    },
)
async def ai_discover_patterns(
    project_id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    current_user: User = require_role("editor"),
):
    # Tenant isolation: verify project belongs to caller's tenant
    proj = (await db.execute(
        select(Project.id).where(Project.id == project_id, Project.kb_id == kb_id)
    )).scalar_one_or_none()
    if proj is None:
        raise NotFoundException(ErrorCode.PROJECT_NOT_FOUND, "Project not found")
    celery = _get_celery_app()
    if celery is None:
        raise AppException(ErrorCode.SYSTEM_INTERNAL_ERROR, "AI 服务不可用", status_code=500)

    result = celery.send_task(
        "orchestrator.discover_patterns",
        args=[str(project_id)],
    )

    try:
        task_result = result.get(timeout=120)
    except Exception as e:
        logger.error("Pattern discovery failed for project %s: %s", project_id, e)
        raise AppException(ErrorCode.SYSTEM_INTERNAL_ERROR, "AI 模式发现失败", status_code=500)

    if task_result.get("status") == "error":
        raise AppException(
            ErrorCode.SYSTEM_INTERNAL_ERROR,
            task_result.get("message", "AI 模式发现失败"),
            status_code=500,
        )

    return DataResponse(data={
        "clusters": task_result.get("clusters", []),
        "frequent_associations": task_result.get("frequent_associations", []),
        "knowledge_gaps": task_result.get("knowledge_gaps", []),
        "analyzed_docs_count": task_result.get("analyzed_docs_count", 0),
    })
