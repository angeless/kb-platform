"""Multi-library routing service: route content to the best-matching project."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_models import Project


class ProjectRouterService:
    """Routes content to the most relevant project using a 2-layer strategy.

    Layer 1: Explicit — user provides project_id directly.
    Layer 2: Keyword matching — compare content keywords against project profiles.
    """

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def route(
        self,
        content_keywords: list[str],
        exclude_project_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Return top-3 candidate projects ranked by keyword overlap.

        Args:
            content_keywords: Keywords extracted from the content to route.
            exclude_project_id: Optionally exclude a project (e.g., source project).

        Returns:
            List of {project_id, project_name, confidence, reason} dicts.
        """
        projects = await self.db.execute(
            select(Project).where(
                Project.tenant_id == self.tenant_id,
                Project.status == "active",
            )
        )

        candidates = []
        content_set = set(k.lower() for k in content_keywords)

        for project in projects.scalars().all():
            if exclude_project_id and project.id == exclude_project_id:
                continue

            # Build project keyword set from profile_keywords + name + industry_hint
            proj_keywords: set[str] = set()
            if project.profile_keywords:
                proj_keywords.update(k.lower() for k in project.profile_keywords)
            proj_keywords.add(project.name.lower())
            if project.industry_hint:
                proj_keywords.add(project.industry_hint.lower())

            overlap = content_set & proj_keywords
            if not overlap:
                continue

            confidence = min(len(overlap) / max(len(content_set), 1), 1.0)
            candidates.append({
                "project_id": str(project.id),
                "project_name": project.name,
                "confidence": round(confidence, 2),
                "reason": f"匹配关键词: {', '.join(list(overlap)[:3])}",
            })

        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        return candidates[:3]
