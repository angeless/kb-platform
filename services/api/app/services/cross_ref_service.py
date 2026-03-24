"""Cross-reference service: CRUD + auto-suggest for document links."""

import uuid

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from shared_models import CrossReference, KnowledgeDoc, DocEmbedding, Project


class CrossRefService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

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
            tenant_id=self.tenant_id,
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
                CrossReference.tenant_id == self.tenant_id,
            )
        )
        # As target
        as_target = await self.db.execute(
            select(CrossReference).where(
                CrossReference.target_doc_id == doc_id,
                CrossReference.tenant_id == self.tenant_id,
            )
        )

        refs = list(as_source.scalars().all()) + list(as_target.scalars().all())
        results = []
        for ref in refs:
            # Enrich with doc titles
            source_doc = await self.db.get(KnowledgeDoc, ref.source_doc_id)
            target_doc = await self.db.get(KnowledgeDoc, ref.target_doc_id)
            target_project = await self.db.get(Project, target_doc.project_id) if target_doc else None

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
                CrossReference.tenant_id == self.tenant_id,
            )
        )
        return result.rowcount > 0

    async def auto_suggest(self, doc_id: uuid.UUID, max_results: int = 5) -> list[dict]:
        """Suggest cross-references based on shared source refs and keyword overlap."""
        doc = await self.db.get(KnowledgeDoc, doc_id)
        if not doc:
            return []

        # Strategy: find docs with overlapping keywords
        candidates = []
        if doc.keywords:
            all_docs = await self.db.execute(
                select(KnowledgeDoc).where(
                    KnowledgeDoc.tenant_id == self.tenant_id,
                    KnowledgeDoc.id != doc_id,
                    KnowledgeDoc.keywords.isnot(None),
                )
            )
            for other in all_docs.scalars().all():
                if not other.keywords:
                    continue
                overlap = set(doc.keywords) & set(other.keywords)
                if len(overlap) >= 2:
                    # Check not already linked
                    existing = await self.db.execute(
                        select(CrossReference.id).where(
                            and_(
                                CrossReference.source_doc_id == doc_id,
                                CrossReference.target_doc_id == other.id,
                            )
                        )
                    )
                    if existing.scalar_one_or_none() is None:
                        candidates.append({
                            "target_doc_id": str(other.id),
                            "target_title": other.title,
                            "relation_type": "related",
                            "confidence": min(len(overlap) / 5.0, 1.0),
                            "reason": f"共享关键词: {', '.join(list(overlap)[:3])}",
                        })

        # Sort by confidence descending
        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        return candidates[:max_results]
