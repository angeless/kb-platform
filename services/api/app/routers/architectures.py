"""Architectures router: list, get, publish, node CRUD."""

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.architecture import ArchitectureOut, NodeCreate, NodeOut, NodeUpdate
from shared_schemas.common import DataResponse, ErrorDetail, ListResponse, PaginationMeta

from app.deps import get_db, get_kb_id, require_role
from shared_models import User
from app.services.architecture_service import ArchitectureService

router = APIRouter(tags=["architectures"])

_RESP_AUTH = {
    401: {"description": "Unauthorized", "model": ErrorDetail},
    403: {"description": "Forbidden", "model": ErrorDetail},
}


@router.get(
    "/v1/projects/{project_id}/architectures",
    response_model=ListResponse[ArchitectureOut],
    summary="List architectures for a project",
    description="Returns all knowledge architecture versions for a project, including drafts and published versions.",
    responses={
        200: {"description": "Architecture list returned"},
        **_RESP_AUTH,
        404: {"description": "Project not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def list_architectures(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
):
    svc = ArchitectureService(db, kb_id)
    archs = await svc.list_by_project(project_id)
    return ListResponse(
        data=[ArchitectureOut.model_validate(a) for a in archs],
        meta=PaginationMeta(page=1, page_size=len(archs), total=len(archs)),
    )


@router.get(
    "/v1/architectures/{arch_id}",
    response_model=DataResponse[ArchitectureOut],
    summary="Get an architecture",
    description="Returns details of a single architecture version by ID.",
    responses={
        200: {"description": "Architecture details returned"},
        **_RESP_AUTH,
        404: {"description": "Architecture not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def get_architecture(
    arch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
):
    svc = ArchitectureService(db, kb_id)
    arch = await svc.get(arch_id)
    return DataResponse(data=ArchitectureOut.model_validate(arch))


@router.get(
    "/v1/architectures/{arch_id}/nodes",
    response_model=ListResponse[NodeOut],
    summary="List architecture nodes",
    description="Returns all nodes (tree structure) of an architecture version.",
    responses={
        200: {"description": "Node list returned"},
        **_RESP_AUTH,
        404: {"description": "Architecture not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def list_nodes(
    arch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
):
    svc = ArchitectureService(db, kb_id)
    nodes = await svc.list_nodes(arch_id)
    return ListResponse(
        data=[NodeOut.model_validate(n) for n in nodes],
        meta=PaginationMeta(page=1, page_size=len(nodes), total=len(nodes)),
    )


@router.post(
    "/v1/architectures/{arch_id}/publish",
    response_model=DataResponse[ArchitectureOut],
    summary="Publish an architecture",
    description="Transitions an architecture from draft to published status. Requires project_admin role.",
    responses={
        200: {"description": "Architecture published"},
        **_RESP_AUTH,
        404: {"description": "Architecture not found", "model": ErrorDetail},
        409: {"description": "Architecture is not in publishable state", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def publish_architecture(
    arch_id: uuid.UUID,
    confirmation_id: str | None = Query(None),
    phrase: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = require_role("project_admin"),
):
    # Confirmation phrase gate — user must type "PUBLISH" to confirm
    from app.utils.confirmation import generate_confirmation, verify_confirmation
    if not confirmation_id or not phrase:
        conf = generate_confirmation("publish_architecture", str(_user.id), "PUBLISH")
        return JSONResponse(status_code=428, content={
            "error": "CONFIRMATION_REQUIRED",
            "message": "请输入 PUBLISH 以确认发布",
            "confirmation_id": conf["confirmation_id"],
            "challenge": "请输入「PUBLISH」以确认发布架构",
            "expires_in": conf["expires_in"],
        })
    if not verify_confirmation(confirmation_id, phrase, str(_user.id)):
        return JSONResponse(status_code=403, content={"error": "CONFIRMATION_INVALID", "message": "确认短语不正确或已过期"})

    svc = ArchitectureService(db, kb_id)
    arch = await svc.publish(arch_id)
    return DataResponse(data=ArchitectureOut.model_validate(arch))


@router.post(
    "/v1/architectures/{arch_id}/nodes",
    response_model=DataResponse[NodeOut],
    status_code=201,
    summary="Create a node",
    description="Adds a new node to an architecture's tree structure. Requires project_admin role.",
    responses={
        201: {"description": "Node created"},
        **_RESP_AUTH,
        404: {"description": "Architecture not found", "model": ErrorDetail},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def create_node(
    arch_id: uuid.UUID,
    body: NodeCreate,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = require_role("project_admin"),
):
    svc = ArchitectureService(db, kb_id)
    node = await svc.create_node(arch_id, body.model_dump())
    return DataResponse(data=NodeOut.model_validate(node))


@router.patch(
    "/v1/architectures/{arch_id}/nodes/{node_id}",
    response_model=DataResponse[NodeOut],
    summary="Update a node",
    description="Partially updates a node's properties (name, description, parent, sort_order). Requires project_admin role.",
    responses={
        200: {"description": "Node updated"},
        **_RESP_AUTH,
        404: {"description": "Architecture or node not found", "model": ErrorDetail},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def update_node(
    arch_id: uuid.UUID,
    node_id: uuid.UUID,
    body: NodeUpdate,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = require_role("project_admin"),
):
    svc = ArchitectureService(db, kb_id)
    node = await svc.update_node(arch_id, node_id, body.model_dump(exclude_unset=True))
    return DataResponse(data=NodeOut.model_validate(node))


@router.post(
    "/v1/architectures/{arch_id}/fork",
    response_model=DataResponse[ArchitectureOut],
    status_code=201,
    summary="Fork an architecture",
    description="Creates a new draft architecture by deep-copying all nodes from an existing version. Requires project_admin role.",
    responses={
        201: {"description": "Architecture forked"},
        **_RESP_AUTH,
        404: {"description": "Architecture not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def fork_architecture(
    arch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = require_role("project_admin"),
):
    svc = ArchitectureService(db, kb_id)
    new_arch = await svc.fork(arch_id)
    return DataResponse(data=ArchitectureOut.model_validate(new_arch))


@router.get(
    "/v1/architectures/{arch_id}/compare/{other_id}",
    response_model=DataResponse,
    summary="Compare two architectures",
    description="Returns a diff between two architecture versions, showing added, removed, and changed nodes.",
    responses={
        200: {"description": "Architecture comparison returned"},
        **_RESP_AUTH,
        404: {"description": "Architecture not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def compare_architectures(
    arch_id: uuid.UUID,
    other_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
):
    svc = ArchitectureService(db, kb_id)
    diff = await svc.compare(arch_id, other_id)
    return DataResponse(data=diff)


@router.post(
    "/v1/architectures/{arch_id}/rollback/{target_id}",
    response_model=DataResponse[ArchitectureOut],
    status_code=201,
    summary="Rollback architecture to a previous version",
    description="Creates a new draft architecture by copying the target version's nodes. Requires project_admin role.",
    responses={
        201: {"description": "Architecture rolled back (new draft created)"},
        **_RESP_AUTH,
        404: {"description": "Architecture not found", "model": ErrorDetail},
        500: {"description": "Internal server error", "model": ErrorDetail},
    },
)
async def rollback_architecture(
    arch_id: uuid.UUID,
    target_id: uuid.UUID,
    confirmation_id: str | None = Query(None),
    phrase: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    kb_id: uuid.UUID = Depends(get_kb_id),
    _user: User = require_role("project_admin"),
):
    # Confirmation phrase gate — user must type "ROLLBACK" to confirm
    from app.utils.confirmation import generate_confirmation, verify_confirmation
    if not confirmation_id or not phrase:
        conf = generate_confirmation("rollback_architecture", str(_user.id), "ROLLBACK")
        return JSONResponse(status_code=428, content={
            "error": "CONFIRMATION_REQUIRED",
            "message": "请输入 ROLLBACK 以确认回滚",
            "confirmation_id": conf["confirmation_id"],
            "challenge": "请输入「ROLLBACK」以确认回滚架构",
            "expires_in": conf["expires_in"],
        })
    if not verify_confirmation(confirmation_id, phrase, str(_user.id)):
        return JSONResponse(status_code=403, content={"error": "CONFIRMATION_INVALID", "message": "确认短语不正确或已过期"})

    svc = ArchitectureService(db, kb_id)
    new_arch = await svc.rollback(arch_id, target_id)
    return DataResponse(data=ArchitectureOut.model_validate(new_arch))
