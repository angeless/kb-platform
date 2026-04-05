"""SKILL CRUD router: list, create, update, delete."""

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ErrorCode, NotFoundException
from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta

from app.deps import get_current_user, get_db, get_kb_id, require_role
from shared_models import Skill, User

router = APIRouter(prefix="/v1/projects/{project_id}/skills", tags=["skills"])


def _skill_to_dict(s: Skill) -> dict:
    return {
        "id": str(s.id), "stage_name": s.stage_name, "name": s.name,
        "description": s.description, "prompt_template": s.prompt_template,
        "input_schema": s.input_schema, "output_schema": s.output_schema,
        "version": s.version, "is_active": s.is_active,
        "created_at": s.created_at.isoformat() if s.created_at else "",
        "updated_at": s.updated_at.isoformat() if s.updated_at else "",
    }


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
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = Depends(get_current_user),
):
    from shared_models import Project
    proj = (await db.execute(
        select(Project).where(Project.id == project_id, Project.kb_id == kb_id)
    )).scalar_one_or_none()
    if proj is None:
        raise NotFoundException(message="项目不存在")
    base = select(Skill).where(Skill.project_id == project_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await db.execute(
        base.order_by(Skill.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return ListResponse(
        data=[_skill_to_dict(s) for s in rows],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )


# --- POST / PUT / DELETE (v0.52.8 — Gap-10 fix) ---


class SkillCreateBody(BaseModel):
    stage_name: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: str | None = None
    prompt_template: str
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)


class SkillUpdateBody(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    prompt_template: str | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    is_active: bool | None = None


@router.post(
    "",
    response_model=DataResponse,
    status_code=201,
    summary="Create a skill",
)
async def create_skill(
    project_id: uuid.UUID,
    body: SkillCreateBody,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = require_role("editor"),
):
    from shared_models import Project
    proj = (await db.execute(
        select(Project).where(Project.id == project_id, Project.kb_id == kb_id)
    )).scalar_one_or_none()
    if proj is None:
        raise NotFoundException(message="项目不存在")
    # Auto-increment version if same project+stage already has skills
    latest = (await db.execute(
        select(func.max(Skill.version)).where(
            Skill.project_id == project_id,
            Skill.stage_name == body.stage_name,
        )
    )).scalar()
    next_version = (latest or 0) + 1

    skill = Skill(
        project_id=project_id,
        stage_name=body.stage_name,
        name=body.name,
        description=body.description,
        prompt_template=body.prompt_template,
        input_schema=body.input_schema,
        output_schema=body.output_schema,
        version=next_version,
    )
    db.add(skill)
    await db.flush()
    return DataResponse(data=_skill_to_dict(skill))


@router.put(
    "/{skill_id}",
    response_model=DataResponse,
    summary="Update a skill",
)
async def update_skill(
    project_id: uuid.UUID,
    skill_id: uuid.UUID,
    body: SkillUpdateBody,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = require_role("editor"),
):
    from shared_models import Project
    proj = (await db.execute(
        select(Project).where(Project.id == project_id, Project.kb_id == kb_id)
    )).scalar_one_or_none()
    if proj is None:
        raise NotFoundException(message="项目不存在")
    skill = (await db.execute(
        select(Skill).where(Skill.id == skill_id, Skill.project_id == project_id)
    )).scalar_one_or_none()
    if skill is None:
        raise NotFoundException(message="Skill 不存在")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(skill, field, value)
    await db.flush()
    return DataResponse(data=_skill_to_dict(skill))


@router.delete(
    "/{skill_id}",
    response_model=DataResponse,
    summary="Delete a skill",
)
async def delete_skill(
    project_id: uuid.UUID,
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = require_role("project_admin"),
):
    from shared_models import Project
    proj = (await db.execute(
        select(Project).where(Project.id == project_id, Project.kb_id == kb_id)
    )).scalar_one_or_none()
    if proj is None:
        raise NotFoundException(message="项目不存在")
    skill = (await db.execute(
        select(Skill).where(Skill.id == skill_id, Skill.project_id == project_id)
    )).scalar_one_or_none()
    if skill is None:
        raise NotFoundException(message="Skill 不存在")

    await db.delete(skill)
    await db.flush()
    return DataResponse(data={"id": str(skill_id), "deleted": True})
