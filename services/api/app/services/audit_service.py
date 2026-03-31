"""Audit log service: write and query audit records."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Write and query audit log entries."""

    def __init__(self, db: AsyncSession, kb_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.db = db
        self.kb_id = kb_id
        self.user_id = user_id

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        detail: dict | None = None,
    ) -> None:
        """Write an audit log entry. Failure is logged but does not raise."""
        try:
            entry = AuditLog(
                id=uuid.uuid4(),
                kb_id=self.kb_id,
                project_id=project_id,
                user_id=self.user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                detail=detail,
            )
            self.db.add(entry)
            await self.db.flush()
        except Exception as e:
            logger.warning("Failed to write audit log: %s", e)

    async def list(
        self,
        project_id: uuid.UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AuditLog], int]:
        """Query audit logs with optional filters."""
        base = select(AuditLog).where(AuditLog.kb_id == self.kb_id)

        if project_id is not None:
            base = base.where(AuditLog.project_id == project_id)
        if action is not None:
            base = base.where(AuditLog.action == action)
        if resource_type is not None:
            base = base.where(AuditLog.resource_type == resource_type)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = base.order_by(AuditLog.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()

        return list(rows), total
