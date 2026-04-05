"""Ontology CRUD router: list concepts and relations, trigger extraction."""

import uuid

from celery import Celery
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import get_settings
from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta

from app.deps import check_feature, get_current_user, get_db, get_kb_id, require_role
from shared_models import OntologyConcept, OntologyRelation, User

router = APIRouter(prefix="/v1/projects/{project_id}/ontology", tags=["ontology"])

# Module-level Celery app for dispatching orchestrator tasks
_celery_app: Celery | None = None


def _get_celery_app() -> Celery:
    global _celery_app
    if _celery_app is None:
        settings = get_settings()
        app = Celery(broker=settings.celery_broker_url)
        if settings.celery_broker_transport_options:
            app.conf.broker_transport_options = settings.celery_broker_transport_options
        _celery_app = app
    return _celery_app


@router.get(
    "/concepts",
    response_model=ListResponse,
    summary="List ontology concepts",
    description="List all concepts in the project's knowledge ontology.",
)
async def list_concepts(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = Depends(get_current_user),
):
    from shared_models import Project
    from shared_errors import NotFoundException
    proj = (await db.execute(
        select(Project).where(Project.id == project_id, Project.kb_id == kb_id)
    )).scalar_one_or_none()
    if proj is None:
        raise NotFoundException(message="项目不存在")
    rows = (await db.execute(
        select(OntologyConcept).where(OntologyConcept.project_id == project_id)
        .order_by(OntologyConcept.name)
    )).scalars().all()
    return ListResponse(
        data=[{
            "id": str(c.id), "name": c.name, "definition": c.definition,
            "concept_type": c.concept_type, "parent_id": str(c.parent_id) if c.parent_id else None,
        } for c in rows],
        meta=PaginationMeta(page=1, page_size=len(rows), total=len(rows)),
    )


@router.get(
    "/relations",
    response_model=ListResponse,
    summary="List ontology relations",
    description="List all relations between concepts in the project's knowledge ontology.",
)
async def list_relations(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = Depends(get_current_user),
):
    from shared_models import Project
    from shared_errors import NotFoundException
    proj = (await db.execute(
        select(Project).where(Project.id == project_id, Project.kb_id == kb_id)
    )).scalar_one_or_none()
    if proj is None:
        raise NotFoundException(message="项目不存在")
    rows = (await db.execute(
        select(OntologyRelation).where(OntologyRelation.project_id == project_id)
    )).scalars().all()
    return ListResponse(
        data=[{
            "id": str(r.id),
            "source_concept_id": str(r.source_concept_id),
            "target_concept_id": str(r.target_concept_id),
            "relation_type": r.relation_type,
            "confidence": r.confidence,
        } for r in rows],
        meta=PaginationMeta(page=1, page_size=len(rows), total=len(rows)),
    )


# --- Trigger extraction (v0.52.7 — Gap-9 fix) ---

from pydantic import BaseModel


class ExtractOntologyRequest(BaseModel):
    doc_id: uuid.UUID


@router.post(
    "/extract",
    response_model=DataResponse,
    status_code=202,
    summary="Trigger ontology extraction for a document",
)
async def extract_ontology(
    project_id: uuid.UUID,
    body: ExtractOntologyRequest,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = require_role("editor"),
    _feature=check_feature("ontology_extraction"),
):
    from shared_models import KnowledgeDoc
    from shared_errors import NotFoundException
    doc = (await db.execute(
        select(KnowledgeDoc).where(
            KnowledgeDoc.id == body.doc_id,
            KnowledgeDoc.project_id == project_id,
        )
    )).scalar_one_or_none()
    if doc is None:
        raise NotFoundException(message="文档不存在或不属于该项目")

    _get_celery_app().send_task(
        "orchestrator.extract_ontology",
        args=[str(project_id), str(body.doc_id)],
        queue="ai",
    )
    return DataResponse(data={"status": "accepted", "doc_id": str(body.doc_id)})
