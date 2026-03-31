"""Pipeline stage configuration router — per-project stage settings."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse
from shared_schemas.pipeline_stage_config import (
    DEFAULT_STAGE_PARAMS,
    STAGE_NAMES,
    PipelineConfigListOut,
    PipelineStageConfigDetailOut,
    PipelineStageConfigOut,
    PipelineStageConfigUpdate,
)

from app.deps import get_db, get_kb_id, require_role
from shared_models import User
from shared_models.pipeline_stage_config import PipelineStageConfig

router = APIRouter(prefix="/v1/projects", tags=["pipeline-config"])


def _build_stage_out(stage_name: str, row: PipelineStageConfig | None) -> PipelineStageConfigOut:
    """Build stage output, filling defaults if no DB record exists."""
    if row is not None:
        return PipelineStageConfigOut(
            stage_name=row.stage_name,
            enabled=row.enabled,
            params=row.params,
        )
    return PipelineStageConfigOut(
        stage_name=stage_name,
        enabled=True,
        params=DEFAULT_STAGE_PARAMS.get(stage_name, {}),
    )


@router.get(
    "/{project_id}/pipeline-config",
    response_model=DataResponse[PipelineConfigListOut],
    summary="Get pipeline stage config for a project",
)
async def get_pipeline_config(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = require_role("viewer"),
):
    result = await db.execute(
        select(PipelineStageConfig).where(PipelineStageConfig.project_id == project_id)
    )
    rows = {r.stage_name: r for r in result.scalars().all()}
    stages = [_build_stage_out(name, rows.get(name)) for name in STAGE_NAMES]
    return DataResponse(data=PipelineConfigListOut(stages=stages))


@router.put(
    "/{project_id}/pipeline-config/{stage_name}",
    response_model=DataResponse[PipelineStageConfigDetailOut],
    summary="Update a specific stage config",
)
async def update_stage_config(
    project_id: uuid.UUID,
    stage_name: str,
    body: PipelineStageConfigUpdate,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = require_role("editor"),
):
    if stage_name not in STAGE_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown stage: {stage_name}")

    result = await db.execute(
        select(PipelineStageConfig).where(
            PipelineStageConfig.project_id == project_id,
            PipelineStageConfig.stage_name == stage_name,
        )
    )
    row = result.scalar_one_or_none()

    if row is None:
        row = PipelineStageConfig(
            project_id=project_id,
            stage_name=stage_name,
            enabled=body.enabled,
            params=body.params,
        )
        db.add(row)
    else:
        row.enabled = body.enabled
        row.params = body.params

    await db.commit()
    await db.refresh(row)
    return DataResponse(data=PipelineStageConfigDetailOut.model_validate(row))


@router.post(
    "/{project_id}/pipeline-config/reset",
    response_model=DataResponse[PipelineConfigListOut],
    summary="Reset pipeline config to defaults",
)
async def reset_pipeline_config(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = require_role("editor"),
):
    result = await db.execute(
        select(PipelineStageConfig).where(PipelineStageConfig.project_id == project_id)
    )
    for row in result.scalars().all():
        await db.delete(row)
    await db.commit()

    stages = [_build_stage_out(name, None) for name in STAGE_NAMES]
    return DataResponse(data=PipelineConfigListOut(stages=stages))
