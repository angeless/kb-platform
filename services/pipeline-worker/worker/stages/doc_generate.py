"""Stage 5: Generate knowledge documents from classified chunks.

Calls AI Orchestrator via Celery to synthesize chunks into structured Markdown documents.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared_models import AssetChunk, KnowledgeDoc, KnowledgeDocVersion, SourceRef

from ..celery_app import celery_app

logger = logging.getLogger(__name__)


def generate_documents(
    db: Session,
    project_id: uuid.UUID,
    architecture_id: uuid.UUID,
    classification: dict,
    user_id: uuid.UUID,
    config: dict | None = None,
) -> list[uuid.UUID]:
    """Generate knowledge documents for new/supplement chunks.

    Dispatches orchestrator.generate_docs via Celery and waits for the result.
    Falls back to local document creation if AI Orchestrator is unavailable.

    Returns:
        List of created/updated KnowledgeDoc IDs.
    """
    new_chunk_ids = classification.get("new", [])
    supplement_chunk_ids = classification.get("supplement", [])
    correction_chunk_ids = classification.get("correction", [])
    new_set = set(new_chunk_ids)
    supplement_set = set(supplement_chunk_ids)
    correction_set = set(correction_chunk_ids)
    all_ids = [uuid.UUID(cid) for cid in new_chunk_ids + supplement_chunk_ids + correction_chunk_ids]

    if not all_ids:
        return []

    def _resolve_update_type(chunk_id_str: str) -> str:
        """Determine update_type from classification result."""
        if chunk_id_str in new_set:
            return "new"
        if chunk_id_str in supplement_set:
            return "supplement"
        if chunk_id_str in correction_set:
            return "correction"
        return "new"

    # Try AI Orchestrator via Celery
    try:
        temp_job_id = str(uuid.uuid4())
        result = celery_app.send_task(
            "orchestrator.generate_docs",
            args=[str(project_id), temp_job_id],
            queue="ai",
        )
        response = result.get(timeout=180)

        if response.get("status") == "success":
            docs_created = response.get("docs_created", 0)
            logger.info("AI Orchestrator generated %d docs for project %s", docs_created, project_id)
            # Orchestrator writes docs directly to DB — refresh and collect doc IDs
            db.expire_all()
            created_docs = db.execute(
                select(KnowledgeDoc).where(
                    KnowledgeDoc.project_id == project_id,
                    KnowledgeDoc.status == "draft",
                )
            ).scalars().all()
            # Backfill update_type for docs missing it (orchestrator may not set it)
            for d in created_docs:
                if d.update_type is None:
                    d.update_type = "new"
            db.flush()
            return [d.id for d in created_docs]
    except Exception as e:
        logger.warning("Doc generation via Celery failed, using fallback: %s", e)

    # Fallback: create raw docs from chunks locally (IR-aware)
    chunks = db.execute(
        select(AssetChunk).where(AssetChunk.id.in_(all_ids))
    ).scalars().all()

    # IR-enriched: sort chunks by structure_type (headings first for better titles)
    _type_order = {"heading": 0, "paragraph": 1, "list": 2, "table": 3, "code": 4, "caption": 5}
    chunks_sorted = sorted(chunks, key=lambda c: _type_order.get(c.structure_type or "paragraph", 9))

    doc_ids = []
    for c in chunks_sorted[:10]:  # Limit fallback
        # IR-enriched: use heading content as document title if available
        title = f"文档-{c.id.hex[:8]}"
        if c.structure_type == "heading" and len(c.content_text) < 100:
            title = c.content_text.strip()

        doc = KnowledgeDoc(
            id=uuid.uuid4(),
            project_id=project_id,
            node_id=None,
            doc_type="topic",
            title=title,
            current_version=1,
            status="draft",
            update_type=_resolve_update_type(str(c.id)),
        )
        db.add(doc)
        db.flush()

        # IR-enriched: annotate low-confidence content
        content = c.content_text
        if c.extraction_confidence is not None and c.extraction_confidence < 0.5:
            content = f"> [OCR uncertainty] 以下内容提取置信度较低，可能存在识别错误。\n\n{content}"

        version = KnowledgeDocVersion(
            id=uuid.uuid4(),
            doc_id=doc.id,
            version=1,
            content_md=content,
            change_reason="Pipeline 自动生成（降级模式）",
            created_by=user_id,
        )
        db.add(version)

        ref = SourceRef(
            id=uuid.uuid4(),
            doc_version_id=version.id,
            asset_chunk_id=c.id,
            location_hint="auto-generated",
        )
        db.add(ref)
        doc_ids.append(doc.id)

    db.flush()
    return doc_ids
