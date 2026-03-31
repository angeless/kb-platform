"""Stage 4: Generate or update knowledge architecture draft.

Calls AI Orchestrator via Celery to propose architecture nodes based on classified content.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared_models import Architecture, ArchitectureNode

from ..celery_app import celery_app

logger = logging.getLogger(__name__)

MAX_ARCH_DEPTH = 5


def validate_architecture(db: Session, arch_id: uuid.UUID) -> dict:
    """Validate architecture quality after generation.

    Checks:
    1. Node depth ≤ MAX_ARCH_DEPTH
    2. No duplicate node names at the same level
    3. No orphan nodes (no children and no docs)
    4. Coverage score present in metadata

    Returns:
        {"passed": bool, "warnings": [...]}
    """
    nodes = db.execute(
        select(ArchitectureNode).where(
            ArchitectureNode.architecture_id == arch_id
        )
    ).scalars().all()

    warnings: list[str] = []

    if not nodes:
        return {"passed": True, "warnings": ["架构无节点（使用了回退方案）"]}

    # Build parent map
    node_map = {n.id: n for n in nodes}
    children_map: dict[uuid.UUID | None, list] = {}
    for n in nodes:
        children_map.setdefault(n.parent_id, []).append(n)

    # 1. Depth check
    def get_depth(node_id: uuid.UUID, current: int = 1) -> int:
        kids = children_map.get(node_id, [])
        if not kids:
            return current
        return max(get_depth(k.id, current + 1) for k in kids)

    roots = [n for n in nodes if n.parent_id is None]
    max_depth = max((get_depth(r.id) for r in roots), default=0)
    if max_depth > MAX_ARCH_DEPTH:
        warnings.append(f"架构深度 {max_depth} 超过上限 {MAX_ARCH_DEPTH}")

    # 2. Duplicate names at same parent
    for parent_id, siblings in children_map.items():
        names = [s.node_name for s in siblings]
        dupes = [n for n in set(names) if names.count(n) > 1]
        if dupes:
            warnings.append(f"同级节点名称重复: {', '.join(dupes)}")

    # 3. Orphan check (leaf nodes — no children)
    leaf_ids = {n.id for n in nodes if n.id not in children_map}
    if leaf_ids:
        from shared_models import KnowledgeDoc
        docs_with_nodes = db.execute(
            select(KnowledgeDoc.node_id).where(
                KnowledgeDoc.node_id.in_(leaf_ids)
            )
        ).scalars().all()
        nodes_with_docs = set(docs_with_nodes)
        orphans = leaf_ids - nodes_with_docs
        if len(orphans) > len(nodes) * 0.5:
            warnings.append(f"{len(orphans)}/{len(nodes)} 个叶子节点无文档（架构可能过于细分）")

    # 4. Coverage metadata
    arch = db.execute(
        select(Architecture).where(Architecture.id == arch_id)
    ).scalar_one_or_none()
    if arch and isinstance(arch.levels_json, dict):
        score = arch.levels_json.get("coverage_score", 0)
        if score < 60:
            warnings.append(f"覆盖度评分偏低: {score}%（建议 ≥ 60%）")

    return {"passed": len(warnings) == 0, "warnings": warnings}


def generate_architecture_draft(
    db: Session,
    project_id: uuid.UUID,
    classification: dict,
    config: dict | None = None,
) -> uuid.UUID:
    """Generate or update architecture draft based on classification results.

    Dispatches orchestrator.propose_architecture via Celery if no architecture exists.

    Returns:
        The architecture ID (existing or newly created).
    """
    # Check for existing architecture (prefer published, fallback to draft)
    arch = db.execute(
        select(Architecture).where(
            Architecture.project_id == project_id,
            Architecture.status == "published",
        ).order_by(Architecture.created_at.desc()).limit(1)
    ).scalar_one_or_none()

    if arch is None:
        arch = db.execute(
            select(Architecture).where(
                Architecture.project_id == project_id,
                Architecture.status == "draft",
            ).order_by(Architecture.created_at.desc()).limit(1)
        ).scalar_one_or_none()

    if arch is not None:
        logger.info("Using existing architecture %s for project %s", arch.id, project_id)
        return arch.id

    # No architecture exists — call AI Orchestrator to propose one
    try:
        # Create a temporary job for the orchestrator task
        temp_job_id = str(uuid.uuid4())
        result = celery_app.send_task(
            "orchestrator.propose_architecture",
            args=[str(project_id), temp_job_id],
            queue="ai",
        )
        response = result.get(timeout=120)

        if response.get("status") == "success":
            arch_id_str = response.get("architecture_id")
            if arch_id_str:
                logger.info("AI Orchestrator proposed architecture %s", arch_id_str)
                # Refresh the session to see the new architecture
                db.expire_all()
                return uuid.UUID(arch_id_str)
    except Exception as e:
        logger.error("Architecture proposal via Celery failed: %s", e)

    # Fallback: create a minimal architecture locally
    arch = Architecture(
        id=uuid.uuid4(),
        project_id=project_id,
        name="自动生成架构",
        version="0.1.0",
        status="draft",
    )
    db.add(arch)
    db.flush()

    # Create a default root node
    root = ArchitectureNode(
        id=uuid.uuid4(),
        architecture_id=arch.id,
        node_name="知识根节点",
        node_type="category",
        level=1,
        description="自动创建的根节点",
        status="draft",
    )
    db.add(root)
    db.flush()

    logger.info("Created fallback architecture %s for project %s", arch.id, project_id)
    return arch.id
