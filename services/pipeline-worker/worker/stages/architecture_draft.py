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


def generate_architecture_draft(
    db: Session,
    project_id: uuid.UUID,
    classification: dict,
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
