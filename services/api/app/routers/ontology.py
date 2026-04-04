"""Ontology CRUD router: list concepts and relations."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta

from app.deps import get_current_user, get_db, get_kb_id
from shared_models import OntologyConcept, OntologyRelation, User

router = APIRouter(prefix="/v1/projects/{project_id}/ontology", tags=["ontology"])


@router.get(
    "/concepts",
    response_model=ListResponse,
    summary="List ontology concepts",
    description="List all concepts in the project's knowledge ontology.",
)
async def list_concepts(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
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
    _user: User = Depends(get_current_user),
):
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
