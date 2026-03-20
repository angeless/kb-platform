"""Architecture service: list, get, publish, node CRUD with tenant isolation."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ConflictException, ErrorCode, NotFoundException
from shared_models import Architecture, ArchitectureNode

from . import TenantService


class ArchitectureService(TenantService):
    """Operations for architectures, scoped to a single tenant."""

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

    async def fork(self, arch_id: uuid.UUID) -> Architecture:
        """Create a new draft version from an existing architecture, deep-copying all nodes."""
        source = await self.get(arch_id)
        source_nodes = await self.list_nodes(arch_id)

        # Bump version: "1.0.0" -> "2.0.0"
        parts = source.version.split(".")
        major = int(parts[0]) + 1 if parts else 1
        new_version = f"{major}.0.0"

        new_arch = Architecture(
            id=uuid.uuid4(),
            project_id=source.project_id,
            name=source.name,
            version=new_version,
            status="draft",
            levels_json=source.levels_json,
        )
        self.db.add(new_arch)
        await self.db.flush()

        # Deep copy nodes, maintaining parent relationships
        old_to_new: dict[uuid.UUID, uuid.UUID] = {}
        # First pass: create all nodes without parent_id
        for node in source_nodes:
            new_id = uuid.uuid4()
            old_to_new[node.id] = new_id
            new_node = ArchitectureNode(
                id=new_id,
                architecture_id=new_arch.id,
                parent_id=None,  # set in second pass
                node_name=node.node_name,
                node_type=node.node_type,
                level=node.level,
                description=node.description,
                accept_types=node.accept_types,
                reject_types=node.reject_types,
                update_policy=node.update_policy,
                review_policy=node.review_policy,
                status="draft",
            )
            self.db.add(new_node)

        await self.db.flush()

        # Second pass: fix parent_id references
        for node in source_nodes:
            if node.parent_id and node.parent_id in old_to_new:
                new_node_id = old_to_new[node.id]
                q = select(ArchitectureNode).where(ArchitectureNode.id == new_node_id)
                new_node = (await self.db.execute(q)).scalar_one()
                new_node.parent_id = old_to_new[node.parent_id]

        await self.db.flush()
        await self.db.refresh(new_arch)
        return new_arch

    async def compare(self, arch_id_a: uuid.UUID, arch_id_b: uuid.UUID) -> dict:
        """Compare two architecture versions by node names. Returns added, removed, modified."""
        nodes_a = await self.list_nodes(arch_id_a)
        nodes_b = await self.list_nodes(arch_id_b)

        map_a = {n.node_name: n for n in nodes_a}
        map_b = {n.node_name: n for n in nodes_b}

        names_a = set(map_a.keys())
        names_b = set(map_b.keys())

        added = [{"node_name": n, "node_type": map_b[n].node_type} for n in names_b - names_a]
        removed = [{"node_name": n, "node_type": map_a[n].node_type} for n in names_a - names_b]
        modified = []
        for name in names_a & names_b:
            na, nb = map_a[name], map_b[name]
            changes = {}
            for field in ("node_type", "level", "description", "status"):
                va, vb = getattr(na, field), getattr(nb, field)
                if va != vb:
                    changes[field] = {"from": va, "to": vb}
            if changes:
                modified.append({"node_name": name, "changes": changes})

        return {"added": added, "removed": removed, "modified": modified}

    async def rollback(self, arch_id: uuid.UUID, target_id: uuid.UUID) -> Architecture:
        """Rollback by forking from a previous version."""
        # Verify both belong to same project
        current = await self.get(arch_id)
        target = await self.get(target_id)
        if current.project_id != target.project_id:
            raise ConflictException(
                error_code=ErrorCode.ARCH_ALREADY_PUBLISHED,
                message="回滚目标必须属于同一项目",
            )
        return await self.fork(target_id)

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
        new_parent_id = node_data.get("parent_id")
        if new_parent_id is not None:
            if new_parent_id == node_id:
                raise ConflictException(
                    error_code=ErrorCode.ARCH_CYCLE_DETECTED,
                    message="节点不能将自身设为父节点",
                )
            current_id = new_parent_id
            for _ in range(50):
                pq = select(ArchitectureNode).where(
                    ArchitectureNode.id == current_id,
                    ArchitectureNode.architecture_id == arch_id,
                )
                parent_node = (await self.db.execute(pq)).scalar_one_or_none()
                if parent_node is None or parent_node.parent_id is None:
                    break
                if parent_node.parent_id == node_id:
                    raise ConflictException(
                        error_code=ErrorCode.ARCH_CYCLE_DETECTED,
                        message="修改父节点会形成循环引用",
                    )
                current_id = parent_node.parent_id
        for key, value in node_data.items():
            if value is not None:
                setattr(node, key, value)
        await self.db.flush()
        await self.db.refresh(node)
        return node
