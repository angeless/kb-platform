"""Graph router: knowledge document graph for visualization."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_models.architecture import ArchitectureNode
from shared_models.cross_reference import CrossReference
from shared_models.knowledge import KnowledgeDoc
from shared_schemas.graph import GraphEdge, GraphNode, GraphResponse

from app.deps import get_current_user, get_db
from shared_models import User

router = APIRouter(prefix="/v1/projects", tags=["graph"])


@router.get(
    "/{project_id}/graph",
    response_model=GraphResponse,
    summary="Get knowledge graph",
    description="Returns nodes and edges for the project knowledge graph visualization.",
)
async def get_project_graph(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GraphResponse:
    # 1. Query docs — if > 500 total, restrict to approved only
    base_filter = [
        KnowledgeDoc.project_id == project_id,
        KnowledgeDoc.status.in_(["approved", "draft"]),
    ]
    count_q = select(KnowledgeDoc.id).where(*base_filter)
    count_result = await db.execute(count_q)
    total = len(count_result.all())

    if total > 500:
        base_filter = [
            KnowledgeDoc.project_id == project_id,
            KnowledgeDoc.status == "approved",
        ]

    docs_q = select(KnowledgeDoc).where(*base_filter)
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

    return GraphResponse(
        nodes=graph_nodes,
        edges=edges,
        node_count=len(graph_nodes),
        edge_count=len(edges),
    )
