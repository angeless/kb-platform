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

from .celery_app import celery_app
from .llm_client import call_llm, parse_json_response
from .prompts import build_propose_prompt, build_generate_doc_prompt

logger = logging.getLogger(__name__)

settings = get_settings()

_sync_engine = create_engine(settings.database_url_sync, pool_size=5, max_overflow=5)


def _get_sync_session() -> Session:
    return Session(_sync_engine)


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

            # Create Architecture
            arch = Architecture(
                id=uuid.uuid4(),
                project_id=project_uuid,
                name=result.get("architecture_name", f"{project.name} 知识系统"),
                version="0.1.0",
                status="draft",
                levels_json=result.get("levels", []),
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

                # Create KnowledgeDoc
                doc_id = uuid.uuid4()
                doc = KnowledgeDoc(
                    id=doc_id,
                    project_id=project_uuid,
                    node_id=node.id,
                    doc_type=result.get("doc_type", node.node_type),
                    title=result.get("title", node.node_name),
                    current_version=1,
                    status="draft",
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


def _update_job_running(session: Session, job_id: uuid.UUID) -> None:
    job = session.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
    if job:
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)


def _update_job_completed(session: Session, job_id: uuid.UUID) -> None:
    job = session.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
    if job:
        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)


def _update_job_failed(session: Session, job_id: uuid.UUID, error_message: str) -> None:
    job = session.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
    if job:
        job.status = "failed"
        job.error_message = error_message
        job.finished_at = datetime.now(timezone.utc)
