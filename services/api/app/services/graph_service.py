"""Graph service: merge and split ArchitectureNode operations."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import AppException, ErrorCode
from shared_models.architecture import ArchitectureNode
from shared_models.knowledge import KnowledgeDoc


class GraphService:
    def __init__(self, db: AsyncSession, kb_id: uuid.UUID):
        self.db = db
        self.kb_id = kb_id

    async def _verify_node(self, node_id: uuid.UUID, project_id: uuid.UUID) -> ArchitectureNode:
        """Verify node exists and belongs to project (via architecture)."""
        from shared_models.architecture import Architecture

        node = await self.db.get(ArchitectureNode, node_id)
        if node is None:
            raise AppException(ErrorCode.ARCH_NODE_NOT_FOUND, status_code=404)
        arch = await self.db.get(Architecture, node.architecture_id)
        if arch is None or arch.project_id != project_id:
            raise AppException(ErrorCode.ARCH_NODE_NOT_FOUND, status_code=404)
        return node

    async def merge_nodes(
        self,
        project_id: uuid.UUID,
        source_node_ids: list[uuid.UUID],
        target_name: str,
        target_node_type: str,
        target_description: str | None = None,
    ) -> ArchitectureNode:
        if len(source_node_ids) < 2:
            raise AppException(ErrorCode.ARCH_INSUFFICIENT_SOURCES, status_code=400)

        # Verify all source nodes
        source_nodes: list[ArchitectureNode] = []
        for nid in source_node_ids:
            node = await self._verify_node(nid, project_id)
            source_nodes.append(node)

        # Determine parent_id: inherit if all sources share the same parent, else null
        parent_ids = {n.parent_id for n in source_nodes}
        new_parent_id = parent_ids.pop() if len(parent_ids) == 1 else None

        # Determine level from parent or default to 0
        new_level = source_nodes[0].level if new_parent_id is not None else 0

        # Create new node
        new_node = ArchitectureNode(
            id=uuid.uuid4(),
            architecture_id=source_nodes[0].architecture_id,
            parent_id=new_parent_id,
            node_name=target_name,
            node_type=target_node_type,
            level=new_level,
            description=target_description,
            status="draft",
        )
        self.db.add(new_node)
        await self.db.flush()

        # Reassign all KnowledgeDocs from source nodes to new node
        await self.db.execute(
            update(KnowledgeDoc)
            .where(KnowledgeDoc.node_id.in_(source_node_ids))
            .values(node_id=new_node.id)
        )

        # Archive source nodes
        await self.db.execute(
            update(ArchitectureNode)
            .where(ArchitectureNode.id.in_(source_node_ids))
            .values(status="archived")
        )

        await self.db.flush()
        return new_node

    async def split_node(
        self,
        project_id: uuid.UUID,
        node_id: uuid.UUID,
        part_a_name: str,
        part_a_type: str,
        part_a_doc_ids: list[uuid.UUID],
        part_b_name: str,
        part_b_type: str,
        part_b_doc_ids: list[uuid.UUID],
    ) -> tuple[ArchitectureNode, ArchitectureNode]:
        # Verify source node
        source_node = await self._verify_node(node_id, project_id)

        # Check doc_ids overlap
        set_a = set(part_a_doc_ids)
        set_b = set(part_b_doc_ids)
        if set_a & set_b:
            raise AppException(ErrorCode.ARCH_DOC_LIST_OVERLAP, status_code=400)

        # Verify completeness: all docs under this node must be covered
        result = await self.db.execute(
            select(KnowledgeDoc.id).where(KnowledgeDoc.node_id == node_id)
        )
        actual_doc_ids = {row[0] for row in result.all()}
        provided = set_a | set_b
        if provided != actual_doc_ids:
            raise AppException(ErrorCode.ARCH_DOC_LIST_INCOMPLETE, status_code=400)

        # Create two new nodes
        node_a = ArchitectureNode(
            id=uuid.uuid4(),
            architecture_id=source_node.architecture_id,
            parent_id=source_node.parent_id,
            node_name=part_a_name,
            node_type=part_a_type,
            level=source_node.level,
            description=None,
            status="draft",
        )
        node_b = ArchitectureNode(
            id=uuid.uuid4(),
            architecture_id=source_node.architecture_id,
            parent_id=source_node.parent_id,
            node_name=part_b_name,
            node_type=part_b_type,
            level=source_node.level,
            description=None,
            status="draft",
        )
        self.db.add(node_a)
        self.db.add(node_b)
        await self.db.flush()

        # Reassign docs
        if part_a_doc_ids:
            await self.db.execute(
                update(KnowledgeDoc)
                .where(KnowledgeDoc.id.in_(part_a_doc_ids))
                .values(node_id=node_a.id)
            )
        if part_b_doc_ids:
            await self.db.execute(
                update(KnowledgeDoc)
                .where(KnowledgeDoc.id.in_(part_b_doc_ids))
                .values(node_id=node_b.id)
            )

        # Archive original node
        source_node.status = "archived"
        await self.db.flush()

        return node_a, node_b
