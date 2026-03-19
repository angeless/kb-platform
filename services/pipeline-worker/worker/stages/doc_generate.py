"""Stage 5: Generate knowledge documents from classified chunks.

Calls AI Orchestrator to synthesize chunks into structured Markdown documents.
"""

import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared_models import ArchitectureNode, AssetChunk, KnowledgeDoc, KnowledgeDocVersion, SourceRef

logger = logging.getLogger(__name__)


def generate_documents(
    db: Session,
    project_id: uuid.UUID,
    architecture_id: uuid.UUID,
    classification: dict,
    orchestrator_url: str,
    user_id: uuid.UUID,
) -> list[uuid.UUID]:
    """Generate knowledge documents for new/supplement chunks.

    Returns:
        List of created/updated KnowledgeDoc IDs.
    """
    new_chunk_ids = classification.get("new", [])
    supplement_chunk_ids = classification.get("supplement", [])
    all_ids = [uuid.UUID(cid) for cid in new_chunk_ids + supplement_chunk_ids]

    if not all_ids:
        return []

    # Load chunks
    chunks = db.execute(
        select(AssetChunk).where(AssetChunk.id.in_(all_ids))
    ).scalars().all()

    chunk_texts = [{"chunk_id": str(c.id), "content": c.content_text} for c in chunks]

    # Load architecture nodes for assignment
    nodes = db.execute(
        select(ArchitectureNode).where(
            ArchitectureNode.architecture_id == architecture_id
        )
    ).scalars().all()
    node_names = [{"node_id": str(n.id), "name": n.node_name, "type": n.node_type} for n in nodes]

    # Call AI Orchestrator for document generation
    try:
        resp = httpx.post(
            f"{orchestrator_url}/generate-docs",
            json={
                "project_id": str(project_id),
                "chunks": chunk_texts,
                "architecture_nodes": node_names,
            },
            timeout=180,
        )
        resp.raise_for_status()
        generated = resp.json().get("documents", [])
    except Exception as e:
        logger.error("Document generation failed: %s", e)
        # Fallback: create raw docs from chunks
        generated = [{
            "title": f"文档-{c.id.hex[:8]}",
            "content_md": c.content_text,
            "doc_type": "topic",
            "node_id": None,
            "source_chunk_ids": [str(c.id)],
        } for c in chunks[:10]]  # Limit fallback

    doc_ids = []
    for doc_data in generated:
        doc = KnowledgeDoc(
            id=uuid.uuid4(),
            project_id=project_id,
            node_id=uuid.UUID(doc_data["node_id"]) if doc_data.get("node_id") else None,
            doc_type=doc_data.get("doc_type", "topic"),
            title=doc_data.get("title", "未命名文档"),
            current_version=1,
            status="draft",
        )
        db.add(doc)
        db.flush()

        version = KnowledgeDocVersion(
            id=uuid.uuid4(),
            doc_id=doc.id,
            version=1,
            content_md=doc_data.get("content_md", ""),
            change_reason="Pipeline 自动生成",
            created_by=user_id,
        )
        db.add(version)

        # Create source references
        for chunk_id_str in doc_data.get("source_chunk_ids", []):
            ref = SourceRef(
                id=uuid.uuid4(),
                doc_version_id=version.id,
                asset_chunk_id=uuid.UUID(chunk_id_str),
                location_hint="auto-generated",
            )
            db.add(ref)

        doc_ids.append(doc.id)

    db.flush()
    return doc_ids
