"""Stage 4: Generate or update knowledge architecture draft.

Calls AI Orchestrator to propose architecture nodes based on classified content.
"""

import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared_models import Architecture, ArchitectureNode

logger = logging.getLogger(__name__)


def generate_architecture_draft(
    db: Session,
    project_id: uuid.UUID,
    classification: dict,
    orchestrator_url: str,
) -> uuid.UUID:
    """Generate or update architecture draft based on classification results.

    Returns:
        The architecture ID (existing or newly created).
    """
    # Find existing draft architecture or create one
    arch = db.execute(
        select(Architecture).where(
            Architecture.project_id == project_id,
            Architecture.status == "draft",
        ).order_by(Architecture.created_at.desc()).limit(1)
    ).scalar_one_or_none()

    if arch is None:
        arch = Architecture(
            id=uuid.uuid4(),
            project_id=project_id,
            name="自动生成架构",
            version="0.1.0",
            status="draft",
        )
        db.add(arch)
        db.flush()

    # Get existing nodes for context
    existing_nodes = db.execute(
        select(ArchitectureNode).where(ArchitectureNode.architecture_id == arch.id)
    ).scalars().all()
    existing = [{"name": n.node_name, "type": n.node_type, "level": n.level} for n in existing_nodes]

    # Call AI Orchestrator for node suggestions
    try:
        resp = httpx.post(
            f"{orchestrator_url}/architecture-draft",
            json={
                "project_id": str(project_id),
                "classification": classification,
                "existing_nodes": existing,
            },
            timeout=120,
        )
        resp.raise_for_status()
        suggestions = resp.json().get("nodes", [])
    except Exception as e:
        logger.error("Architecture draft generation failed: %s", e)
        suggestions = []

    # Create suggested nodes that don't already exist
    existing_names = {n.node_name for n in existing_nodes}
    for node_data in suggestions:
        name = node_data.get("node_name", "")
        if name and name not in existing_names:
            node = ArchitectureNode(
                id=uuid.uuid4(),
                architecture_id=arch.id,
                node_name=name,
                node_type=node_data.get("node_type", "topic"),
                level=node_data.get("level", 1),
                description=node_data.get("description", ""),
                status="draft",
            )
            db.add(node)
            existing_names.add(name)

    db.flush()
    return arch.id
