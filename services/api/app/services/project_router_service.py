"""Multi-library routing service: route content to the best-matching project.

Three-layer strategy per plan:
  Layer 1: Explicit — user provides project_id directly (handled by caller)
  Layer 2: Semantic — embedding similarity against project profiles
  Layer 3: Rule-based — keyword/file-type matching (v0.43 scope, not implemented)
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_models import Project
from app.utils.math_utils import cosine_similarity


class ProjectRouterService:
    def __init__(self, db: AsyncSession, kb_id: uuid.UUID):
        self.db = db
        self.kb_id = kb_id

    async def route(
        self,
        content_embedding: list[float] | None = None,
        content_keywords: list[str] | None = None,
        exclude_project_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Return top-3 candidate projects using Layer 2 routing.

        Combines embedding similarity (if available) with keyword overlap.
        Embedding match has higher weight (0.7) vs keyword match (0.3).

        Routing thresholds per plan:
          > 0.7  → auto-route candidate
          0.4-0.7 → recommend for user confirmation
          < 0.4  → suggest creating new project
        """
        projects_result = await self.db.execute(
            select(Project).where(
                Project.kb_id == self.kb_id,
                Project.status == "active",
            )
        )

        candidates = []

        for project in projects_result.scalars().all():
            if exclude_project_id and project.id == exclude_project_id:
                continue

            emb_score = 0.0
            kw_score = 0.0
            reasons = []

            # Layer 2a: Embedding similarity against project profile
            if content_embedding and project.profile_embedding:
                emb_score = cosine_similarity(content_embedding, project.profile_embedding)
                if emb_score > 0.3:
                    reasons.append(f"语义相似度: {emb_score:.2f}")

            # Layer 2b: Keyword overlap (supplementary signal)
            if content_keywords:
                proj_keywords: set[str] = set()
                if project.profile_keywords:
                    proj_keywords.update(k.lower() for k in project.profile_keywords)
                proj_keywords.add(project.name.lower())
                if project.industry_hint:
                    proj_keywords.add(project.industry_hint.lower())
                if project.description:
                    # Extract simple words from description as fallback keywords
                    proj_keywords.update(
                        w.lower() for w in project.description.split() if len(w) > 2
                    )

                content_set = set(k.lower() for k in content_keywords)
                overlap = content_set & proj_keywords
                if overlap:
                    kw_score = min(len(overlap) / max(len(content_set), 1), 1.0)
                    reasons.append(f"关键词匹配({len(overlap)}): {', '.join(list(overlap)[:3])}")

            # Weighted score: embedding 70%, keywords 30%
            if emb_score > 0 and kw_score > 0:
                final_score = emb_score * 0.7 + kw_score * 0.3
            elif emb_score > 0:
                final_score = emb_score
            elif kw_score > 0:
                final_score = kw_score
            else:
                continue

            # Determine routing action per plan thresholds
            if final_score > 0.7:
                action = "auto_route"
            elif final_score >= 0.4:
                action = "recommend"
            else:
                action = "low_confidence"

            candidates.append({
                "project_id": str(project.id),
                "project_name": project.name,
                "confidence": round(final_score, 3),
                "action": action,
                "reason": " + ".join(reasons) if reasons else "低置信度匹配",
            })

        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        return candidates[:3]
