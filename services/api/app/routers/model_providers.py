"""Model providers and routes router."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ListResponse, PaginationMeta
from shared_schemas.model_config import (
    ModelProviderCreate,
    ModelProviderOut,
    ModelProviderTestRequest,
    ModelRouteCreate,
    ModelRouteOut,
    ModelRouteUpdate,
)

from app.deps import get_current_user, get_db, get_tenant_id
from app.services.audit_service import AuditService
from app.services.model_provider_service import ModelProviderService
from shared_models import User

router = APIRouter(tags=["model-providers"])


@router.post("/v1/model-providers", response_model=DataResponse[ModelProviderOut], status_code=201)
async def create_provider(
    body: ModelProviderCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
):
    svc = ModelProviderService(db, tenant_id)
    provider_dict = await svc.create_provider(body.model_dump())
    audit = AuditService(db, tenant_id, current_user.id)
    await audit.log("create", "model_provider", provider_dict["id"])
    return DataResponse(data=ModelProviderOut.model_validate(provider_dict))


@router.get("/v1/model-providers", response_model=ListResponse[ModelProviderOut])
async def list_providers(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ModelProviderService(db, tenant_id)
    providers = await svc.list_providers()
    return ListResponse(
        data=[ModelProviderOut.model_validate(p) for p in providers],
        meta=PaginationMeta(page=1, page_size=len(providers), total=len(providers)),
    )


@router.post("/v1/model-providers/test", response_model=DataResponse)
async def test_provider(
    body: ModelProviderTestRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ModelProviderService(db, tenant_id)
    result = await svc.test_provider(body.provider_id)
    return DataResponse(data=result)


@router.post("/v1/model-routes", response_model=DataResponse[ModelRouteOut], status_code=201)
async def create_route(
    body: ModelRouteCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ModelProviderService(db, tenant_id)
    route = await svc.create_route(body.model_dump())
    return DataResponse(data=ModelRouteOut.model_validate(route))


@router.get("/v1/model-routes", response_model=ListResponse[ModelRouteOut])
async def list_routes(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ModelProviderService(db, tenant_id)
    routes = await svc.list_routes()
    return ListResponse(
        data=[ModelRouteOut.model_validate(r) for r in routes],
        meta=PaginationMeta(page=1, page_size=len(routes), total=len(routes)),
    )


@router.patch("/v1/model-routes/{route_id}", response_model=DataResponse[ModelRouteOut])
async def update_route(
    route_id: uuid.UUID,
    body: ModelRouteUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ModelProviderService(db, tenant_id)
    route = await svc.update_route(route_id, body.model_dump(exclude_unset=True))
    return DataResponse(data=ModelRouteOut.model_validate(route))


@router.delete("/v1/model-routes/{route_id}", response_model=DataResponse)
async def delete_route(
    route_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ModelProviderService(db, tenant_id)
    await svc.delete_route(route_id)
    return DataResponse(data={"deleted": True})
