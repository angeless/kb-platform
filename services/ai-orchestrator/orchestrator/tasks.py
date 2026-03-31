"""Celery tasks for the AI orchestrator."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from shared_config.settings import get_settings
from shared_models import (
    Architecture, ArchitectureNode, AssetChunk, Asset, Job, Project,
    KnowledgeDoc, KnowledgeDocVersion, SourceRef, ConflictRecord,
)
from shared_models.pipeline_stage_config import PipelineStageConfig

from .celery_app import celery_app
from .llm_client import call_llm, parse_json_response
from .prompts import (
    build_propose_prompt,
    build_generate_doc_prompt,
    build_classify_prompt,
    build_summary_prompt,
    build_suggest_tags_prompt,
    build_summary_reflection_prompt,
    build_tags_reflection_prompt,
)

logger = logging.getLogger(__name__)

settings = get_settings()

_sync_engine = create_engine(settings.database_url_sync, pool_size=5, max_overflow=5)


def _get_sync_session() -> Session:
    return Session(_sync_engine)


def _get_entity_types(session: Session, project_id: uuid.UUID, stage_name: str) -> list[str] | None:
    """Load entity_types from pipeline stage config for a project.

    Returns None if not configured or empty, so callers can use default behavior.
    """
    row = session.execute(
        select(PipelineStageConfig).where(
            PipelineStageConfig.project_id == project_id,
            PipelineStageConfig.stage_name == stage_name,
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    types = row.params.get("entity_types", [])
    return types if types else None


@celery_app.task(bind=True, name="orchestrator.propose_architecture")
def propose_architecture(self, project_id: str, job_id: str) -> dict:
    """Generate an initial knowledge system architecture for a project.

    1. Collect all parsed chunks from the project's assets
    2. Build prompt from chunks
    3. Call LLM to propose architecture
    4. Parse JSON response
    5. Write Architecture + ArchitectureNode records
    6. Update Job status

    This task is idempotent: re-running deletes any existing draft architecture.
    """
    project_uuid = uuid.UUID(project_id)
    job_uuid = uuid.UUID(job_id)

    with _get_sync_session() as session:
        # Load project
        project = session.execute(
            select(Project).where(Project.id == project_uuid)
        ).scalar_one_or_none()

        if project is None:
            _update_job_failed(session, job_uuid, f"Project {project_id} not found")
            return {"status": "error", "message": "Project not found"}

        # Update job to running
        _update_job_running(session, job_uuid)
        session.commit()

        try:
            # Collect chunks from all parsed assets in the project
            asset_ids = session.execute(
                select(Asset.id).where(
                    Asset.project_id == project_uuid,
                    Asset.parse_status == "parsed",
                )
            ).scalars().all()

            if not asset_ids:
                raise ValueError("项目中没有已解析的资料，请先上传并解析资料")

            chunks = session.execute(
                select(AssetChunk).where(
                    AssetChunk.asset_id.in_(asset_ids)
                ).order_by(AssetChunk.asset_id, AssetChunk.chunk_index)
            ).scalars().all()

            chunk_dicts = [
                {"content_text": c.content_text, "page_or_timestamp": c.page_or_timestamp}
                for c in chunks
            ]

            # Build prompt
            system_prompt, user_prompt = build_propose_prompt(
                project_name=project.name,
                industry_hint=project.industry_hint,
                chunks=chunk_dicts,
            )

            # Call LLM
            llm_response = call_llm(prompt=user_prompt, system_prompt=system_prompt)
            result = parse_json_response(llm_response)

            # Delete existing draft architectures for idempotency
            existing_drafts = session.execute(
                select(Architecture).where(
                    Architecture.project_id == project_uuid,
                    Architecture.status == "draft",
                )
            ).scalars().all()
            for draft in existing_drafts:
                session.execute(
                    delete(ArchitectureNode).where(
                        ArchitectureNode.architecture_id == draft.id
                    )
                )
                session.delete(draft)

            # Create Architecture with MECE metadata
            arch = Architecture(
                id=uuid.uuid4(),
                project_id=project_uuid,
                name=result.get("architecture_name", f"{project.name} 知识系统"),
                version="0.1.0",
                status="draft",
                levels_json={
                    "levels": result.get("levels", []),
                    "classification_dimension": result.get("classification_dimension", "topic"),
                    "dimension_rationale": result.get("dimension_rationale", ""),
                    "coverage_score": result.get("coverage_score", 0),
                    "uncovered_chunks": result.get("uncovered_chunks", []),
                },
            )
            session.add(arch)
            session.flush()

            # Create nodes
            node_name_to_id: dict[str, uuid.UUID] = {}
            nodes_data = result.get("nodes", [])

            for node_data in nodes_data:
                node_id = uuid.uuid4()
                parent_name = node_data.get("parent_name")
                parent_id = node_name_to_id.get(parent_name) if parent_name else None

                node = ArchitectureNode(
                    id=node_id,
                    architecture_id=arch.id,
                    parent_id=parent_id,
                    node_name=node_data.get("node_name", "未命名"),
                    node_type=node_data.get("node_type", "category"),
                    level=node_data.get("level", 1),
                    description=node_data.get("description", ""),
                    accept_types=node_data.get("accept_types"),
                    status="draft",
                )
                session.add(node)
                node_name_to_id[node.node_name] = node_id

            # Update job
            _update_job_completed(session, job_uuid)
            session.commit()

            logger.info(
                "Architecture proposed for project %s: %s with %d nodes",
                project_id, arch.name, len(nodes_data),
            )
            return {
                "status": "success",
                "architecture_id": str(arch.id),
                "name": arch.name,
                "nodes_count": len(nodes_data),
            }

        except Exception as e:
            session.rollback()
            with _get_sync_session() as err_session:
                _update_job_failed(err_session, job_uuid, str(e))
                err_session.commit()

            logger.error("Failed to propose architecture for project %s: %s", project_id, e)
            return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="orchestrator.generate_docs")
def generate_docs(self, project_id: str, job_id: str) -> dict:
    """Generate knowledge documents for each architecture node in a project.

    1. Load the latest architecture (prefer published, fallback to draft)
    2. Load all parsed asset chunks
    3. For each leaf node, call LLM to generate a knowledge document
    4. Write KnowledgeDoc + KnowledgeDocVersion + SourceRef records
    5. Record conflicts if detected
    6. Update Job status

    This task is idempotent: re-running deletes existing draft documents.
    """
    project_uuid = uuid.UUID(project_id)
    job_uuid = uuid.UUID(job_id)

    with _get_sync_session() as session:
        # Load project
        project = session.execute(
            select(Project).where(Project.id == project_uuid)
        ).scalar_one_or_none()

        if project is None:
            _update_job_failed(session, job_uuid, f"Project {project_id} not found")
            session.commit()
            return {"status": "error", "message": "Project not found"}

        # Update job to running
        _update_job_running(session, job_uuid)
        session.commit()

        try:
            # Find architecture: prefer published, fallback to draft
            arch = session.execute(
                select(Architecture).where(
                    Architecture.project_id == project_uuid,
                    Architecture.status == "published",
                ).order_by(Architecture.created_at.desc())
            ).scalar_one_or_none()

            if arch is None:
                arch = session.execute(
                    select(Architecture).where(
                        Architecture.project_id == project_uuid,
                        Architecture.status == "draft",
                    ).order_by(Architecture.created_at.desc())
                ).scalar_one_or_none()

            if arch is None:
                raise ValueError("项目中没有架构，请先生成架构")

            # Load architecture nodes
            nodes = session.execute(
                select(ArchitectureNode).where(
                    ArchitectureNode.architecture_id == arch.id
                ).order_by(ArchitectureNode.level, ArchitectureNode.node_name)
            ).scalars().all()

            if not nodes:
                raise ValueError("架构中没有节点")

            # Collect all parsed chunks
            asset_ids = session.execute(
                select(Asset.id).where(
                    Asset.project_id == project_uuid,
                    Asset.parse_status == "parsed",
                )
            ).scalars().all()

            all_chunks = []
            if asset_ids:
                all_chunks = session.execute(
                    select(AssetChunk).where(
                        AssetChunk.asset_id.in_(asset_ids)
                    ).order_by(AssetChunk.asset_id, AssetChunk.chunk_index)
                ).scalars().all()

            if not all_chunks:
                raise ValueError("项目中没有已解析的资料片段")

            # Build chunk dicts with index
            chunk_dicts = [
                {
                    "index": i,
                    "content_text": c.content_text,
                    "page_or_timestamp": c.page_or_timestamp,
                    "chunk_id": c.id,
                }
                for i, c in enumerate(all_chunks)
            ]

            # Delete existing draft docs for idempotency
            existing_drafts = session.execute(
                select(KnowledgeDoc).where(
                    KnowledgeDoc.project_id == project_uuid,
                    KnowledgeDoc.status == "draft",
                )
            ).scalars().all()
            for draft_doc in existing_drafts:
                # Delete versions (cascade should handle, but be explicit)
                for ver in draft_doc.versions:
                    session.execute(
                        delete(SourceRef).where(
                            SourceRef.doc_version_id == ver.id
                        )
                    )
                session.execute(
                    delete(KnowledgeDocVersion).where(
                        KnowledgeDocVersion.doc_id == draft_doc.id
                    )
                )
                session.delete(draft_doc)
            session.flush()

            # Generate docs for each node
            docs_created = 0
            conflicts_created = 0

            # Get created_by from job
            job = session.execute(
                select(Job).where(Job.id == job_uuid)
            ).scalar_one_or_none()
            created_by = job.created_by if job else project_uuid  # fallback

            # Load entity_types from pipeline config (v0.46.3)
            doc_gen_entity_types = _get_entity_types(session, project_uuid, "doc_generate")

            for node in nodes:
                # Skip category nodes (they are containers, not content)
                if node.node_type == "category":
                    continue

                # Build prompt for this node
                system_prompt, user_prompt = build_generate_doc_prompt(
                    node_name=node.node_name,
                    node_type=node.node_type,
                    node_description=node.description,
                    node_level=node.level,
                    chunks=chunk_dicts,
                    entity_types=doc_gen_entity_types,
                )

                # Call LLM
                llm_response = call_llm(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                )
                result = parse_json_response(llm_response)

                content_md = result.get("content_md", "")
                if not content_md:
                    logger.info("Skipping node %s: LLM returned empty content", node.node_name)
                    continue

                # Create KnowledgeDoc with knowledge metadata
                doc_id = uuid.uuid4()
                doc = KnowledgeDoc(
                    id=doc_id,
                    project_id=project_uuid,
                    node_id=node.id,
                    doc_type=result.get("doc_type", node.node_type),
                    title=result.get("title", node.node_name),
                    current_version=1,
                    status="draft",
                    keywords=result.get("keywords"),
                    knowledge_type=result.get("knowledge_type"),
                )
                session.add(doc)
                session.flush()

                # Create KnowledgeDocVersion
                version_id = uuid.uuid4()
                version = KnowledgeDocVersion(
                    id=version_id,
                    doc_id=doc_id,
                    version=1,
                    content_md=content_md,
                    change_reason="AI 初次生成",
                    created_by=created_by,
                )
                session.add(version)
                session.flush()

                # Create SourceRefs
                cited_indices = result.get("cited_chunk_indices", [])
                for idx in cited_indices:
                    if 0 <= idx < len(chunk_dicts):
                        ref = SourceRef(
                            id=uuid.uuid4(),
                            doc_version_id=version_id,
                            asset_chunk_id=chunk_dicts[idx]["chunk_id"],
                            location_hint=chunk_dicts[idx].get("page_or_timestamp"),
                        )
                        session.add(ref)

                docs_created += 1

                # Handle conflicts
                if result.get("has_conflicts") and result.get("conflict_description"):
                    conflict = ConflictRecord(
                        id=uuid.uuid4(),
                        project_id=project_uuid,
                        node_id=node.id,
                        description=result["conflict_description"],
                        status="open",
                    )
                    session.add(conflict)
                    conflicts_created += 1

            # Update job
            _update_job_completed(session, job_uuid)
            session.commit()

            logger.info(
                "Generated %d docs (%d conflicts) for project %s",
                docs_created, conflicts_created, project_id,
            )
            return {
                "status": "success",
                "docs_created": docs_created,
                "conflicts_created": conflicts_created,
            }

        except Exception as e:
            session.rollback()
            with _get_sync_session() as err_session:
                _update_job_failed(err_session, job_uuid, str(e))
                err_session.commit()

            logger.error("Failed to generate docs for project %s: %s", project_id, e)
            return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="orchestrator.classify_incremental")
def classify_incremental(self, project_id: str, job_id: str, asset_ids: list[str]) -> dict:
    """Classify new assets against existing knowledge documents.

    For each new chunk, determines if it is:
    - new: no matching topic → create new KnowledgeDoc
    - supplement: adds to existing topic → append new Version to existing Doc
    - correction: updates outdated knowledge → append correction Version
    - conflict: contradicts existing → create ConflictRecord

    This task is idempotent via job status tracking.
    """
    project_uuid = uuid.UUID(project_id)
    job_uuid = uuid.UUID(job_id)
    asset_uuids = [uuid.UUID(aid) for aid in asset_ids]

    with _get_sync_session() as session:
        # Load project
        project = session.execute(
            select(Project).where(Project.id == project_uuid)
        ).scalar_one_or_none()

        if project is None:
            _update_job_failed(session, job_uuid, f"Project {project_id} not found")
            session.commit()
            return {"status": "error", "message": "Project not found"}

        # Update job to running
        _update_job_running(session, job_uuid)
        session.commit()

        try:
            # Get created_by from job
            job = session.execute(
                select(Job).where(Job.id == job_uuid)
            ).scalar_one_or_none()
            created_by = job.created_by if job else project_uuid

            # Collect new chunks from specified assets
            new_chunks_rows = session.execute(
                select(AssetChunk).where(
                    AssetChunk.asset_id.in_(asset_uuids)
                ).order_by(AssetChunk.asset_id, AssetChunk.chunk_index)
            ).scalars().all()

            if not new_chunks_rows:
                raise ValueError("指定的资料中没有已解析的片段")

            new_chunk_dicts = [
                {
                    "index": i,
                    "content_text": c.content_text,
                    "page_or_timestamp": c.page_or_timestamp,
                    "chunk_id": c.id,
                }
                for i, c in enumerate(new_chunks_rows)
            ]

            # Load existing knowledge docs with latest version summary
            existing_docs_rows = session.execute(
                select(KnowledgeDoc).where(
                    KnowledgeDoc.project_id == project_uuid,
                )
            ).scalars().all()

            existing_doc_dicts = []
            for doc in existing_docs_rows:
                # Get latest version summary (first 200 chars)
                latest_ver = None
                if doc.versions:
                    latest_ver = max(doc.versions, key=lambda v: v.version)
                summary = ""
                if latest_ver:
                    summary = latest_ver.content_md[:200]
                    if len(latest_ver.content_md) > 200:
                        summary += "..."

                existing_doc_dicts.append({
                    "doc_id": str(doc.id),
                    "title": doc.title,
                    "summary": summary,
                })

            # Load entity_types from pipeline config (v0.46.3)
            classify_entity_types = _get_entity_types(session, project_uuid, "classify")

            # Build prompt and call LLM
            system_prompt, user_prompt = build_classify_prompt(
                existing_docs=existing_doc_dicts,
                new_chunks=new_chunk_dicts,
                entity_types=classify_entity_types,
            )

            llm_response = call_llm(prompt=user_prompt, system_prompt=system_prompt)
            result = parse_json_response(llm_response)

            # Process classifications
            classifications = result.get("classifications", [])
            new_count = 0
            supplement_count = 0
            correction_count = 0
            conflict_count = 0

            # Load architecture for new docs (use latest)
            arch = session.execute(
                select(Architecture).where(
                    Architecture.project_id == project_uuid,
                ).order_by(Architecture.created_at.desc())
            ).scalar_one_or_none()

            for cls in classifications:
                chunk_idx = cls.get("chunk_index", -1)
                if chunk_idx < 0 or chunk_idx >= len(new_chunk_dicts):
                    continue

                relation = cls.get("relation_type", "new")
                target_doc_id = cls.get("target_doc_id")
                reason = cls.get("reason", "")

                if relation == "new":
                    # Create new KnowledgeDoc + Version
                    doc_id = uuid.uuid4()
                    doc = KnowledgeDoc(
                        id=doc_id,
                        project_id=project_uuid,
                        node_id=None,
                        doc_type="topic",
                        title=f"新增知识 - {new_chunk_dicts[chunk_idx]['content_text'][:50]}",
                        current_version=1,
                        status="draft",
                    )
                    session.add(doc)
                    session.flush()

                    ver = KnowledgeDocVersion(
                        id=uuid.uuid4(),
                        doc_id=doc_id,
                        version=1,
                        content_md=new_chunk_dicts[chunk_idx]["content_text"],
                        change_reason=f"增量接入 - 新增: {reason}",
                        created_by=created_by,
                    )
                    session.add(ver)
                    session.flush()

                    # Add source ref
                    session.add(SourceRef(
                        id=uuid.uuid4(),
                        doc_version_id=ver.id,
                        asset_chunk_id=new_chunk_dicts[chunk_idx]["chunk_id"],
                        location_hint=new_chunk_dicts[chunk_idx].get("page_or_timestamp"),
                    ))
                    new_count += 1

                elif relation in ("supplement", "correction") and target_doc_id:
                    # Append new version to existing doc
                    try:
                        target_uuid = uuid.UUID(target_doc_id)
                    except ValueError:
                        continue

                    target_doc = session.execute(
                        select(KnowledgeDoc).where(KnowledgeDoc.id == target_uuid)
                    ).scalar_one_or_none()

                    if target_doc is None:
                        continue

                    new_ver_num = target_doc.current_version + 1
                    change_label = "补充" if relation == "supplement" else "修正"

                    ver = KnowledgeDocVersion(
                        id=uuid.uuid4(),
                        doc_id=target_uuid,
                        version=new_ver_num,
                        content_md=new_chunk_dicts[chunk_idx]["content_text"],
                        change_reason=f"增量接入 - {change_label}: {reason}",
                        created_by=created_by,
                    )
                    session.add(ver)

                    target_doc.current_version = new_ver_num
                    session.flush()

                    # Add source ref
                    session.add(SourceRef(
                        id=uuid.uuid4(),
                        doc_version_id=ver.id,
                        asset_chunk_id=new_chunk_dicts[chunk_idx]["chunk_id"],
                        location_hint=new_chunk_dicts[chunk_idx].get("page_or_timestamp"),
                    ))

                    if relation == "supplement":
                        supplement_count += 1
                    else:
                        correction_count += 1

                elif relation == "conflict":
                    conflict_desc = cls.get("conflict_description", reason)
                    session.add(ConflictRecord(
                        id=uuid.uuid4(),
                        project_id=project_uuid,
                        node_id=None,
                        description=conflict_desc,
                        status="open",
                    ))
                    conflict_count += 1

            _update_job_completed(session, job_uuid)
            session.commit()

            logger.info(
                "Incremental classification for project %s: new=%d, supplement=%d, correction=%d, conflict=%d",
                project_id, new_count, supplement_count, correction_count, conflict_count,
            )
            return {
                "status": "success",
                "new": new_count,
                "supplement": supplement_count,
                "correction": correction_count,
                "conflict": conflict_count,
            }

        except Exception as e:
            session.rollback()
            with _get_sync_session() as err_session:
                _update_job_failed(err_session, job_uuid, str(e))
                err_session.commit()

            logger.error("Failed incremental classification for project %s: %s", project_id, e)
            return {"status": "error", "message": str(e)}


def _publish_job_event(job: Job, error_message: str | None = None) -> None:
    """Publish job status change to Redis for WebSocket subscribers."""
    try:
        import json
        import redis
        r = redis.from_url(settings.redis_url)
        event = json.dumps({
            "event": "job_status_changed",
            "job_id": str(job.id),
            "project_id": str(job.project_id),
            "status": job.status,
            "job_type": job.job_type,
            "error_message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        r.publish(f"job_events:{job.project_id}", event)
        r.close()
    except Exception as e:
        logger.debug("Failed to publish job event: %s", e)


def _update_job_running(session: Session, job_id: uuid.UUID) -> None:
    job = session.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
    if job:
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        _publish_job_event(job)


def _update_job_completed(session: Session, job_id: uuid.UUID) -> None:
    job = session.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
    if job:
        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        _publish_job_event(job)


def _update_job_failed(session: Session, job_id: uuid.UUID, error_message: str) -> None:
    job = session.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
    if job:
        job.status = "failed"
        job.error_message = error_message
        job.finished_at = datetime.now(timezone.utc)
        _publish_job_event(job, error_message)


# ---------------------------------------------------------------------------
# AI summary / tag suggestion tasks (v0.45.5)
# ---------------------------------------------------------------------------


_REFLECTION_CONFIDENCE_THRESHOLD = 0.7


@celery_app.task(bind=True, name="orchestrator.generate_summary")
def generate_summary(self, doc_id: str) -> dict:
    """Generate an AI summary with one round of reflection/self-check.

    Flow: generate → reflect → decide (use revised if confidence < threshold).
    Writes summary + summary_confidence to KnowledgeDoc.
    """
    doc_uuid = uuid.UUID(doc_id)

    with _get_sync_session() as session:
        doc = session.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.id == doc_uuid)
        ).scalar_one_or_none()

        if doc is None:
            return {"status": "error", "message": "Document not found"}

        latest_version = session.execute(
            select(KnowledgeDocVersion)
            .where(KnowledgeDocVersion.doc_id == doc_uuid)
            .order_by(KnowledgeDocVersion.version.desc())
        ).scalar_one_or_none()

        if latest_version is None or not latest_version.content_md:
            return {"status": "error", "message": "Document has no content"}

        try:
            # Step 1: Initial generation
            system_prompt, user_prompt = build_summary_prompt(latest_version.content_md)
            llm_response = call_llm(prompt=user_prompt, system_prompt=system_prompt)
            result = parse_json_response(llm_response)
            raw_summary = result.get("summary", "")

            if not raw_summary:
                return {"status": "error", "message": "LLM returned empty summary"}

            # Step 2: Reflection (self-check)
            confidence = 0.5  # default if reflection fails
            final_summary = raw_summary
            try:
                ref_system, ref_user = build_summary_reflection_prompt(
                    latest_version.content_md, raw_summary
                )
                ref_response = call_llm(prompt=ref_user, system_prompt=ref_system)
                ref_result = parse_json_response(ref_response)

                confidence = float(ref_result.get("confidence", 0.5))
                confidence = max(0.0, min(1.0, confidence))

                # Step 3: Decide — use revised if low confidence
                if confidence < _REFLECTION_CONFIDENCE_THRESHOLD:
                    revised = ref_result.get("revised_summary")
                    if revised and isinstance(revised, str) and len(revised) > 10:
                        final_summary = revised
                        logger.info(
                            "Doc %s: using revised summary (confidence=%.2f)",
                            doc_id, confidence,
                        )
            except Exception as ref_err:
                logger.warning(
                    "Reflection failed for doc %s, using raw summary: %s",
                    doc_id, ref_err,
                )

            # Step 4: Write to DB
            doc.summary = final_summary
            doc.summary_confidence = confidence
            session.commit()

            logger.info(
                "Generated summary for doc %s (%d chars, confidence=%.2f)",
                doc_id, len(final_summary), confidence,
            )
            return {
                "status": "success",
                "summary": final_summary,
                "confidence": confidence,
            }

        except Exception as e:
            session.rollback()
            logger.error("Failed to generate summary for doc %s: %s", doc_id, e)
            return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="orchestrator.suggest_tags")
def suggest_tags(self, doc_id: str) -> dict:
    """Suggest keyword tags with one round of reflection/self-check.

    Flow: generate → reflect → decide (use revised if confidence < threshold).
    Writes keywords + summary_confidence to KnowledgeDoc.
    """
    doc_uuid = uuid.UUID(doc_id)

    with _get_sync_session() as session:
        doc = session.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.id == doc_uuid)
        ).scalar_one_or_none()

        if doc is None:
            return {"status": "error", "message": "Document not found"}

        latest_version = session.execute(
            select(KnowledgeDocVersion)
            .where(KnowledgeDocVersion.doc_id == doc_uuid)
            .order_by(KnowledgeDocVersion.version.desc())
        ).scalar_one_or_none()

        if latest_version is None or not latest_version.content_md:
            return {"status": "error", "message": "Document has no content"}

        try:
            # Load entity_types from pipeline config (v0.46.3)
            tags_entity_types = _get_entity_types(session, doc.project_id, "classify")

            # Step 1: Initial generation
            system_prompt, user_prompt = build_suggest_tags_prompt(
                latest_version.content_md, entity_types=tags_entity_types,
            )
            llm_response = call_llm(prompt=user_prompt, system_prompt=system_prompt)
            result = parse_json_response(llm_response)

            raw_keywords = result.get("keywords", [])
            if not raw_keywords:
                return {"status": "error", "message": "LLM returned empty keywords"}

            # Step 2: Reflection (self-check)
            confidence = 0.5  # default if reflection fails
            final_keywords = raw_keywords
            try:
                ref_system, ref_user = build_tags_reflection_prompt(
                    latest_version.content_md, raw_keywords
                )
                ref_response = call_llm(prompt=ref_user, system_prompt=ref_system)
                ref_result = parse_json_response(ref_response)

                confidence = float(ref_result.get("confidence", 0.5))
                confidence = max(0.0, min(1.0, confidence))

                # Step 3: Decide — use revised if low confidence
                if confidence < _REFLECTION_CONFIDENCE_THRESHOLD:
                    revised = ref_result.get("revised_tags")
                    if revised and isinstance(revised, list) and len(revised) >= 2:
                        final_keywords = revised
                        logger.info(
                            "Doc %s: using revised tags (confidence=%.2f)",
                            doc_id, confidence,
                        )
            except Exception as ref_err:
                logger.warning(
                    "Reflection failed for doc %s, using raw tags: %s",
                    doc_id, ref_err,
                )

            # Step 4: Write to DB
            doc.keywords = final_keywords
            doc.summary_confidence = confidence
            session.commit()

            logger.info(
                "Suggested %d tags for doc %s (confidence=%.2f)",
                len(final_keywords), doc_id, confidence,
            )
            return {
                "status": "success",
                "keywords": final_keywords,
                "confidence": confidence,
            }

        except Exception as e:
            session.rollback()
            logger.error("Failed to suggest tags for doc %s: %s", doc_id, e)
            return {"status": "error", "message": str(e)}
