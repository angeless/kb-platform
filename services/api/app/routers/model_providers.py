"""Model providers and routes router."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta
from shared_schemas.model_config import (
    ModelProviderCreate,
    ModelProviderOut,
    ModelProviderTestRequest,
    ModelRouteCreate,
    ModelRouteOut,
    ModelRouteUpdate,
)

from app.deps import get_current_user, get_db, get_kb_id, require_role
from app.services.audit_service import AuditService
from app.services.model_provider_service import ModelProviderService
from shared_models import User

router = APIRouter(tags=["model-providers"])

_RESP_AUTH = {
    401: {"description": "Unauthorized", "model": ErrorDetail},
    403: {"description": "Forbidden", "model": ErrorDetail},
}


@router.post(
    "/v1/model-providers",
    response_model=DataResponse[ModelProviderOut],
    status_code=201,
    summary="Create a model provider",
    description="Registers an AI model provider (e.g., OpenAI, Azure OpenAI) with encrypted API credentials. Requires tenant_admin role.",
    responses={
        201: {"description": "Provider created"},
        **_RESP_AUTH,
        409: {"description": "Provider with same name already exists", "model": ErrorDetail},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def create_provider(
    body: ModelProviderCreate,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    current_user: User = require_role("tenant_admin"),
):
    svc = ModelProviderService(db, kb_id)
    provider_dict = await svc.create_provider(body.model_dump())
    audit = AuditService(db, kb_id, current_user.id)
    await audit.log("create", "model_provider", provider_dict["id"])
    return DataResponse(data=ModelProviderOut.model_validate(provider_dict))


@router.get(
    "/v1/model-providers",
    response_model=ListResponse[ModelProviderOut],
    summary="List model providers",
    description="Returns all registered AI model providers for the current tenant.",
    responses={
        200: {"description": "Provider list returned"},
        **_RESP_AUTH,
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def list_providers(
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
):
    svc = ModelProviderService(db, kb_id)
    providers = await svc.list_providers()
    return ListResponse(
        data=[ModelProviderOut.model_validate(p) for p in providers],
        meta=PaginationMeta(page=1, page_size=len(providers), total=len(providers)),
    )


@router.post(
    "/v1/model-providers/test",
    response_model=DataResponse,
    summary="Test a model provider",
    description="Sends a test request to verify the model provider's API connectivity and credentials.",
    responses={
        200: {"description": "Test result returned"},
        **_RESP_AUTH,
        404: {"description": "Provider not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def test_provider(
    body: ModelProviderTestRequest,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
):
    svc = ModelProviderService(db, kb_id)
    result = await svc.test_provider(body.provider_id)
    return DataResponse(data=result)


@router.post(
    "/v1/model-routes",
    response_model=DataResponse[ModelRouteOut],
    status_code=201,
    summary="Create a model route",
    description="Creates a routing rule that maps a task type (e.g., embedding, classification) to a specific model provider. Requires tenant_admin role.",
    responses={
        201: {"description": "Route created"},
        **_RESP_AUTH,
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def create_route(
    body: ModelRouteCreate,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = require_role("tenant_admin"),
):
    svc = ModelProviderService(db, kb_id)
    route = await svc.create_route(body.model_dump())
    return DataResponse(data=ModelRouteOut.model_validate(route))


@router.get(
    "/v1/model-routes",
    response_model=ListResponse[ModelRouteOut],
    summary="List model routes",
    description="Returns all model routing rules for the current tenant.",
    responses={
        200: {"description": "Route list returned"},
        **_RESP_AUTH,
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def list_routes(
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
):
    svc = ModelProviderService(db, kb_id)
    routes = await svc.list_routes()
    return ListResponse(
        data=[ModelRouteOut.model_validate(r) for r in routes],
        meta=PaginationMeta(page=1, page_size=len(routes), total=len(routes)),
    )


@router.patch(
    "/v1/model-routes/{route_id}",
    response_model=DataResponse[ModelRouteOut],
    summary="Update a model route",
    description="Partially updates a model routing rule. Requires tenant_admin role.",
    responses={
        200: {"description": "Route updated"},
        **_RESP_AUTH,
        404: {"description": "Route not found", "model": ErrorDetail},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def update_route(
    route_id: uuid.UUID,
    body: ModelRouteUpdate,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = require_role("tenant_admin"),
):
    svc = ModelProviderService(db, kb_id)
    route = await svc.update_route(route_id, body.model_dump(exclude_unset=True))
    return DataResponse(data=ModelRouteOut.model_validate(route))


@router.delete(
    "/v1/model-routes/{route_id}",
    response_model=DataResponse,
    summary="Delete a model route",
    description="Removes a model routing rule. Requires tenant_admin role.",
    responses={
        200: {"description": "Route deleted"},
        **_RESP_AUTH,
        404: {"description": "Route not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def delete_route(
    route_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = require_role("tenant_admin"),
):
    svc = ModelProviderService(db, kb_id)
    await svc.delete_route(route_id)
    return DataResponse(data={"deleted": True})
