"""Architecture service: list, get, publish, node CRUD with tenant isolation."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ConflictException, ErrorCode, NotFoundException
from shared_models import Architecture, ArchitectureNode, Project


class ArchitectureService:
    """Operations for architectures, scoped to a single tenant."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def _verify_project(self, project_id: uuid.UUID) -> Project:
        """Verify project exists and belongs to tenant."""
        q = select(Project).where(
            Project.id == project_id,
            Project.tenant_id == self.tenant_id,
            Project.status != "deleted",
        )
        result = await self.db.execute(q)
        project = result.scalar_one_or_none()
        if project is None:
            raise NotFoundException(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                message="项目不存在",
            )
        return project

    async def list_by_project(self, project_id: uuid.UUID) -> list[Architecture]:
        """List architectures for a project."""
        await self._verify_project(project_id)
        q = select(Architecture).where(
            Architecture.project_id == project_id,
        ).order_by(Architecture.created_at.desc())
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows)

    async def get(self, arch_id: uuid.UUID) -> Architecture:
        """Get architecture with nodes. Verify via project->tenant chain."""
        q = select(Architecture).where(Architecture.id == arch_id)
        result = await self.db.execute(q)
        arch = result.scalar_one_or_none()
        if arch is None:
            raise NotFoundException(
                error_code=ErrorCode.ARCH_NOT_FOUND,
                message="架构不存在",
            )
        await self._verify_project(arch.project_id)
        return arch

    async def publish(self, arch_id: uuid.UUID) -> Architecture:
        """Set architecture status to 'published'. Only from 'draft' or 'reviewing'."""
        arch = await self.get(arch_id)
        if arch.status not in ("draft", "reviewing"):
            raise ConflictException(
                error_code=ErrorCode.ARCH_ALREADY_PUBLISHED,
                message="当前状态的架构不能发布",
            )
        arch.status = "published"
        await self.db.flush()
        await self.db.refresh(arch)
        return arch

    async def list_nodes(self, arch_id: uuid.UUID) -> list[ArchitectureNode]:
        """List all nodes for an architecture, ordered by level then name."""
        await self.get(arch_id)  # verify exists and tenant access
        q = (
            select(ArchitectureNode)
            .where(ArchitectureNode.architecture_id == arch_id)
            .order_by(ArchitectureNode.level, ArchitectureNode.node_name)
        )
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows)

    async def create_node(self, arch_id: uuid.UUID, node_data: dict) -> ArchitectureNode:
        """Create a node under an architecture."""
        await self.get(arch_id)  # verify exists and tenant access
        node = ArchitectureNode(
            id=uuid.uuid4(),
            architecture_id=arch_id,
            **node_data,
        )
        self.db.add(node)
        await self.db.flush()
        return node

    async def update_node(
        self, arch_id: uuid.UUID, node_id: uuid.UUID, node_data: dict
    ) -> ArchitectureNode:
        """Update node fields."""
        await self.get(arch_id)  # verify exists and tenant access
        q = select(ArchitectureNode).where(
            ArchitectureNode.id == node_id,
            ArchitectureNode.architecture_id == arch_id,
        )
        result = await self.db.execute(q)
        node = result.scalar_one_or_none()
        if node is None:
            raise NotFoundException(
                error_code=ErrorCode.ARCH_NODE_NOT_FOUND,
                message="架构节点不存在",
            )
        for key, value in node_data.items():
            if value is not None:
                setattr(node, key, value)
        await self.db.flush()
        await self.db.refresh(node)
        return node
