"""Graph router: knowledge document graph for visualization, merge, and split."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import AppException, ErrorCode
from shared_models import Project, User
from shared_models.architecture import ArchitectureNode
from shared_models.cross_reference import CrossReference
from shared_models.knowledge import KnowledgeDoc
from shared_schemas.architecture import MergeNodesRequest, NodeOut, SplitNodeRequest
from shared_schemas.common import DataResponse, ERROR_RESPONSES_AUTH
from shared_schemas.graph import GraphEdge, GraphNode, GraphResponse

from app.deps import get_current_user, get_db, get_tenant_id, require_role
from app.services.graph_service import GraphService

router = APIRouter(prefix="/v1/projects", tags=["graph"])


@router.get(
    "/{project_id}/graph",
    response_model=DataResponse[GraphResponse],
    summary="Get knowledge graph",
    description="Returns nodes and edges for the project knowledge graph visualization.",
    responses={**ERROR_RESPONSES_AUTH},
)
async def get_project_graph(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify project exists and belongs to user's tenant
    proj = await db.get(Project, project_id)
    if proj is None or proj.tenant_id != current_user.tenant_id:
        raise AppException(ErrorCode.PROJECT_NOT_FOUND, "项目不存在", status_code=404)

    # 1. Query docs — if > 500 total, restrict to approved only
    base_filter = [
        KnowledgeDoc.project_id == project_id,
        KnowledgeDoc.status.in_(["approved", "draft"]),
    ]
    count_q = select(func.count()).select_from(KnowledgeDoc).where(*base_filter)
    count_result = await db.execute(count_q)
    total = count_result.scalar() or 0

    if total > 500:
        base_filter = [
            KnowledgeDoc.project_id == project_id,
            KnowledgeDoc.status == "approved",
        ]

    docs_q = select(KnowledgeDoc).where(*base_filter).limit(1000)
    docs_result = await db.execute(docs_q)
    docs = docs_result.scalars().all()

    doc_ids = {d.id for d in docs}

    # 2. Batch-load architecture nodes for path building
    node_ids = {d.node_id for d in docs if d.node_id is not None}
    arch_nodes_by_id: dict[uuid.UUID, ArchitectureNode] = {}

    if node_ids:
        # Load referenced nodes, then iteratively load parents until roots
        ids_to_load = set(node_ids)
        while ids_to_load:
            arch_q = select(ArchitectureNode).where(ArchitectureNode.id.in_(ids_to_load))
            arch_result = await db.execute(arch_q)
            loaded = arch_result.scalars().all()
            ids_to_load = set()
            for n in loaded:
                arch_nodes_by_id[n.id] = n
                if n.parent_id and n.parent_id not in arch_nodes_by_id:
                    ids_to_load.add(n.parent_id)

    def _build_path(node_id: uuid.UUID | None) -> list[str]:
        if node_id is None or node_id not in arch_nodes_by_id:
            return []
        path: list[str] = []
        cur = node_id
        while cur and cur in arch_nodes_by_id:
            path.append(arch_nodes_by_id[cur].node_name)
            cur = arch_nodes_by_id[cur].parent_id
        path.reverse()
        return path

    # Build graph nodes
    graph_nodes = [
        GraphNode(
            id=str(d.id),
            label=d.title,
            node_type="doc",
            node_path=_build_path(d.node_id),
            status=d.status,
        )
        for d in docs
    ]

    # 3. Query cross references within this doc set
    edges: list[GraphEdge] = []
    if doc_ids:
        xref_q = select(CrossReference).where(
            CrossReference.source_doc_id.in_(doc_ids),
            CrossReference.target_doc_id.in_(doc_ids),
        )
        xref_result = await db.execute(xref_q)
        xrefs = xref_result.scalars().all()
        edges = [
            GraphEdge(
                id=str(x.id),
                source=str(x.source_doc_id),
                target=str(x.target_doc_id),
                edge_type="cross_ref",
                relation_type=x.relation_type,
            )
            for x in xrefs
        ]

    return DataResponse(
        data=GraphResponse(
            nodes=graph_nodes,
            edges=edges,
            node_count=len(graph_nodes),
            edge_count=len(edges),
        )
    )


@router.post(
    "/{project_id}/graph/nodes/merge",
    response_model=DataResponse[NodeOut],
    status_code=201,
    summary="Merge architecture nodes",
    description="Merge 2+ architecture nodes into one. Reassigns all docs to the new node and archives the source nodes.",
    responses={**ERROR_RESPONSES_AUTH},
)
async def merge_nodes(
    project_id: uuid.UUID,
    body: MergeNodesRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(require_role("project_admin")),
):
    svc = GraphService(db, tenant_id)
    new_node = await svc.merge_nodes(
        project_id=project_id,
        source_node_ids=body.source_node_ids,
        target_name=body.target_name,
        target_node_type=body.target_node_type,
        target_description=body.target_description,
    )
    await db.commit()
    await db.refresh(new_node)
    return DataResponse(data=NodeOut.model_validate(new_node))


@router.post(
    "/{project_id}/graph/nodes/{node_id}/split",
    response_model=DataResponse[list[NodeOut]],
    status_code=201,
    summary="Split architecture node",
    description="Split one architecture node into two. Reassigns docs as specified and archives the original node.",
    responses={**ERROR_RESPONSES_AUTH},
)
async def split_node(
    project_id: uuid.UUID,
    node_id: uuid.UUID,
    body: SplitNodeRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: User = Depends(require_role("project_admin")),
):
    svc = GraphService(db, tenant_id)
    node_a, node_b = await svc.split_node(
        project_id=project_id,
        node_id=node_id,
        part_a_name=body.part_a.name,
        part_a_type=body.part_a.node_type,
        part_a_doc_ids=body.part_a.doc_ids,
        part_b_name=body.part_b.name,
        part_b_type=body.part_b.node_type,
        part_b_doc_ids=body.part_b.doc_ids,
    )
    await db.commit()
    await db.refresh(node_a)
    await db.refresh(node_b)
    return DataResponse(data=[
        NodeOut.model_validate(node_a),
        NodeOut.model_validate(node_b),
    ])
