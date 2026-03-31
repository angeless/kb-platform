"""Cross-reference service: CRUD + auto-suggest for document links."""

import uuid
from typing import Any

from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from shared_models import CrossReference, KnowledgeDoc, KnowledgeDocVersion, SourceRef, DocEmbedding, Project
from app.utils.math_utils import cosine_similarity


class CrossRefService:
    def __init__(self, db: AsyncSession, kb_id: uuid.UUID):
        self.db = db
        self.kb_id = kb_id

    async def create(
        self,
        source_doc_id: uuid.UUID,
        target_doc_id: uuid.UUID,
        relation_type: str,
        confidence: float = 1.0,
        note: str | None = None,
        created_by: str = "user",
    ) -> CrossReference:
        ref = CrossReference(
            id=uuid.uuid4(),
            kb_id=self.kb_id,
            source_doc_id=source_doc_id,
            target_doc_id=target_doc_id,
            relation_type=relation_type,
            confidence=confidence,
            created_by=created_by,
            note=note,
        )
        self.db.add(ref)
        await self.db.flush()
        return ref

    async def list_for_doc(self, doc_id: uuid.UUID) -> list[dict]:
        """Get all cross-references where doc is source or target, enriched with titles."""
        # As source
        as_source = await self.db.execute(
            select(CrossReference).where(
                CrossReference.source_doc_id == doc_id,
                CrossReference.kb_id == self.kb_id,
            )
        )
        # As target
        as_target = await self.db.execute(
            select(CrossReference).where(
                CrossReference.target_doc_id == doc_id,
                CrossReference.kb_id == self.kb_id,
            )
        )

        refs = list(as_source.scalars().all()) + list(as_target.scalars().all())

        # Batch-load all referenced doc IDs
        all_doc_ids = set()
        for ref in refs:
            all_doc_ids.add(ref.source_doc_id)
            all_doc_ids.add(ref.target_doc_id)

        docs_result = await self.db.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.id.in_(all_doc_ids))
        )
        doc_map = {d.id: d for d in docs_result.scalars().all()}

        # Batch-load project info for target docs
        project_ids = {d.project_id for d in doc_map.values() if d.project_id}
        projects_result = await self.db.execute(
            select(Project).where(Project.id.in_(project_ids))
        )
        project_map = {p.id: p for p in projects_result.scalars().all()}

        results = []
        for ref in refs:
            source_doc = doc_map.get(ref.source_doc_id)
            target_doc = doc_map.get(ref.target_doc_id)
            target_project = project_map.get(target_doc.project_id) if target_doc else None

            results.append({
                "id": str(ref.id),
                "source_doc_id": str(ref.source_doc_id),
                "target_doc_id": str(ref.target_doc_id),
                "relation_type": ref.relation_type,
                "confidence": ref.confidence,
                "created_by": ref.created_by,
                "note": ref.note,
                "source_title": source_doc.title if source_doc else None,
                "target_title": target_doc.title if target_doc else None,
                "target_project_id": str(target_doc.project_id) if target_doc else None,
                "target_project_name": target_project.name if target_project else None,
            })
        return results

    async def delete(self, ref_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            delete(CrossReference).where(
                CrossReference.id == ref_id,
                CrossReference.kb_id == self.kb_id,
            )
        )
        return result.rowcount > 0

    async def auto_suggest(self, doc_id: uuid.UUID, max_results: int = 5) -> list[dict]:
        """Suggest cross-references using 3 strategies per plan:
        1. Embedding similarity > 0.75
        2. Keyword intersection >= 3
        3. Shared source material (asset_chunk_id overlap)
        """
        doc = await self.db.get(KnowledgeDoc, doc_id)
        if not doc:
            return []

        # Collect already-linked doc ids to exclude (both directions)
        existing_as_source = await self.db.execute(
            select(CrossReference.target_doc_id).where(
                CrossReference.source_doc_id == doc_id,
                CrossReference.kb_id == self.kb_id,
            )
        )
        existing_as_target = await self.db.execute(
            select(CrossReference.source_doc_id).where(
                CrossReference.target_doc_id == doc_id,
                CrossReference.kb_id == self.kb_id,
            )
        )
        linked_ids = {row[0] for row in existing_as_source.all()}
        linked_ids.update(row[0] for row in existing_as_target.all())
        linked_ids.add(doc_id)  # exclude self

        seen: dict[str, dict] = {}  # target_doc_id -> best candidate

        def _add_candidate(target_id: str, title: str, confidence: float, reason: str) -> None:
            if uuid.UUID(target_id) in linked_ids:
                return
            if target_id not in seen or seen[target_id]["confidence"] < confidence:
                seen[target_id] = {
                    "target_doc_id": target_id,
                    "target_title": title,
                    "relation_type": "related",
                    "confidence": round(confidence, 3),
                    "reason": reason,
                }

        # --- Strategy 1: Embedding similarity > 0.75 ---
        doc_emb = await self.db.execute(
            select(DocEmbedding).where(DocEmbedding.doc_id == doc_id)
        )
        doc_emb_row = doc_emb.scalar_one_or_none()
        if doc_emb_row and doc_emb_row.embedding:
            source_vec = doc_emb_row.embedding
            all_embs = await self.db.execute(
                select(DocEmbedding).where(
                    DocEmbedding.project_id.in_(
                        select(KnowledgeDoc.project_id).where(
                            KnowledgeDoc.kb_id == self.kb_id
                        )
                    ),
                    DocEmbedding.doc_id != doc_id,
                ).limit(500)
            )
            # Collect candidate doc IDs for batch loading
            emb_candidates = []
            for emb in all_embs.scalars().all():
                if not emb.embedding:
                    continue
                sim = cosine_similarity(source_vec, emb.embedding)
                if sim > 0.75:
                    emb_candidates.append((emb.doc_id, sim))

            if emb_candidates:
                emb_doc_ids = [ec[0] for ec in emb_candidates]
                emb_docs_result = await self.db.execute(
                    select(KnowledgeDoc).where(KnowledgeDoc.id.in_(emb_doc_ids))
                )
                emb_doc_map = {d.id: d for d in emb_docs_result.scalars().all()}
                for emb_doc_id, sim in emb_candidates:
                    target_doc = emb_doc_map.get(emb_doc_id)
                    if target_doc:
                        _add_candidate(
                            str(emb_doc_id),
                            target_doc.title,
                            sim,
                            f"语义相似度: {sim:.2f}",
                        )

        # --- Strategy 2: Keyword intersection >= 3 ---
        if doc.keywords:
            doc_kw_set = set(doc.keywords)
            all_docs = await self.db.execute(
                select(KnowledgeDoc).where(
                    KnowledgeDoc.kb_id == self.kb_id,
                    KnowledgeDoc.id != doc_id,
                    KnowledgeDoc.keywords.isnot(None),
                )
            )
            for other in all_docs.scalars().all():
                if not other.keywords:
                    continue
                overlap = doc_kw_set & set(other.keywords)
                if len(overlap) >= 3:
                    _add_candidate(
                        str(other.id),
                        other.title,
                        min(len(overlap) / 5.0, 1.0),
                        f"共享关键词({len(overlap)}): {', '.join(list(overlap)[:3])}",
                    )

        # --- Strategy 3: Shared source material ---
        # Find asset_chunk_ids referenced by this doc's latest version
        latest_ver = await self.db.execute(
            select(KnowledgeDocVersion).where(
                KnowledgeDocVersion.doc_id == doc_id
            ).order_by(KnowledgeDocVersion.version.desc()).limit(1)
        )
        ver = latest_ver.scalar_one_or_none()
        if ver:
            source_chunks = await self.db.execute(
                select(SourceRef.asset_chunk_id).where(
                    SourceRef.doc_version_id == ver.id
                )
            )
            my_chunk_ids = {row[0] for row in source_chunks.all()}
            if my_chunk_ids:
                # Find other doc versions that reference the same chunks
                shared_refs = await self.db.execute(
                    select(SourceRef.doc_version_id, SourceRef.asset_chunk_id).where(
                        SourceRef.asset_chunk_id.in_(my_chunk_ids),
                        SourceRef.doc_version_id != ver.id,
                    )
                )
                # Group by doc_version_id -> count shared chunks
                version_overlap: dict[uuid.UUID, int] = {}
                for row in shared_refs.all():
                    version_overlap[row[0]] = version_overlap.get(row[0], 0) + 1

                for ver_id, count in version_overlap.items():
                    other_ver = await self.db.get(KnowledgeDocVersion, ver_id)
                    if not other_ver:
                        continue
                    other_doc = await self.db.get(KnowledgeDoc, other_ver.doc_id)
                    if not other_doc or other_doc.kb_id != self.kb_id:
                        continue
                    _add_candidate(
                        str(other_doc.id),
                        other_doc.title,
                        min(count / len(my_chunk_ids), 1.0),
                        f"共享来源素材: {count} 个片段",
                    )

        # Sort by confidence descending, return top N
        candidates = sorted(seen.values(), key=lambda x: x["confidence"], reverse=True)
        return candidates[:max_results]

    async def get_project_graph(self, project_id: uuid.UUID) -> dict:
        """Get cross-reference graph data for a project.

        Returns nodes (docs) and edges (cross-refs) for visualization.
        """
        # Get all docs in the project
        docs_result = await self.db.execute(
            select(KnowledgeDoc).where(
                KnowledgeDoc.project_id == project_id,
                KnowledgeDoc.kb_id == self.kb_id,
            )
        )
        docs = docs_result.scalars().all()
        doc_ids = {d.id for d in docs}

        nodes = [
            {"id": str(d.id), "title": d.title, "doc_type": d.doc_type, "status": d.status}
            for d in docs
        ]

        # Get all cross-refs where source or target is in this project
        refs_result = await self.db.execute(
            select(CrossReference).where(
                CrossReference.kb_id == self.kb_id,
                or_(
                    CrossReference.source_doc_id.in_(doc_ids),
                    CrossReference.target_doc_id.in_(doc_ids),
                ),
            )
        )
        refs = refs_result.scalars().all()

        # Add external nodes (docs from other projects referenced)
        external_ids = set()
        for ref in refs:
            if ref.source_doc_id not in doc_ids:
                external_ids.add(ref.source_doc_id)
            if ref.target_doc_id not in doc_ids:
                external_ids.add(ref.target_doc_id)

        for ext_id in external_ids:
            ext_doc = await self.db.get(KnowledgeDoc, ext_id)
            if ext_doc:
                ext_project = await self.db.get(Project, ext_doc.project_id)
                nodes.append({
                    "id": str(ext_doc.id),
                    "title": ext_doc.title,
                    "doc_type": ext_doc.doc_type,
                    "status": ext_doc.status,
                    "external_project": ext_project.name if ext_project else None,
                })

        edges = [
            {
                "source": str(ref.source_doc_id),
                "target": str(ref.target_doc_id),
                "relation_type": ref.relation_type,
                "confidence": ref.confidence,
            }
            for ref in refs
        ]

        return {"nodes": nodes, "edges": edges}
