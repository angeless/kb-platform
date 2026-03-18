"""Architectures router: list, get, publish, node CRUD."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.architecture import ArchitectureOut, NodeCreate, NodeOut, NodeUpdate
from shared_schemas.common import DataResponse, ListResponse, PaginationMeta

from app.deps import get_current_user, get_db, get_tenant_id
from app.services.architecture_service import ArchitectureService

router = APIRouter(tags=["architectures"])


@router.get(
    "/v1/projects/{project_id}/architectures",
    response_model=ListResponse[ArchitectureOut],
)
async def list_architectures(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ArchitectureService(db, tenant_id)
    archs = await svc.list_by_project(project_id)
    return ListResponse(
        data=[ArchitectureOut.model_validate(a) for a in archs],
        meta=PaginationMeta(page=1, page_size=len(archs), total=len(archs)),
    )


@router.get(
    "/v1/architectures/{arch_id}",
    response_model=DataResponse[ArchitectureOut],
)
async def get_architecture(
    arch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ArchitectureService(db, tenant_id)
    arch = await svc.get(arch_id)
    return DataResponse(data=ArchitectureOut.model_validate(arch))


@router.post(
    "/v1/architectures/{arch_id}/publish",
    response_model=DataResponse[ArchitectureOut],
)
async def publish_architecture(
    arch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ArchitectureService(db, tenant_id)
    arch = await svc.publish(arch_id)
    return DataResponse(data=ArchitectureOut.model_validate(arch))


@router.post(
    "/v1/architectures/{arch_id}/nodes",
    response_model=DataResponse[NodeOut],
    status_code=201,
)
async def create_node(
    arch_id: uuid.UUID,
    body: NodeCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ArchitectureService(db, tenant_id)
    node = await svc.create_node(arch_id, body.model_dump())
    return DataResponse(data=NodeOut.model_validate(node))


@router.patch(
    "/v1/architectures/{arch_id}/nodes/{node_id}",
    response_model=DataResponse[NodeOut],
)
async def update_node(
    arch_id: uuid.UUID,
    node_id: uuid.UUID,
    body: NodeUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ArchitectureService(db, tenant_id)
    node = await svc.update_node(arch_id, node_id, body.model_dump(exclude_unset=True))
    return DataResponse(data=NodeOut.model_validate(node))
