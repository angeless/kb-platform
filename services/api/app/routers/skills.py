"""SKILL CRUD router: list, create, update, delete."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta

from app.deps import get_current_user, get_db, get_kb_id, require_role
from shared_models import Skill, User

router = APIRouter(prefix="/v1/projects/{project_id}/skills", tags=["skills"])


@router.get(
    "",
    response_model=ListResponse,
    summary="List skills",
    description="List all skills for a project.",
)
async def list_skills(
    project_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    base = select(Skill).where(Skill.project_id == project_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await db.execute(
        base.order_by(Skill.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return ListResponse(
        data=[{
            "id": str(s.id), "stage_name": s.stage_name, "name": s.name,
            "description": s.description, "prompt_template": s.prompt_template,
            "version": s.version, "is_active": s.is_active,
            "created_at": s.created_at.isoformat() if s.created_at else "",
        } for s in rows],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )
