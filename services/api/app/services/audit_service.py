"""Audit log service: write and query audit records."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import get_settings
from shared_models import AuditLog

logger = logging.getLogger(__name__)

CLEANUP_BATCH_SIZE = 1000


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


async def cleanup_old_audit_logs(db: AsyncSession) -> int:
    """Delete audit logs older than the configured retention period.

    Deletes in batches of CLEANUP_BATCH_SIZE to avoid long table locks.
    Returns total number of deleted rows.
    """
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.audit_retention_days)
    total_deleted = 0

    while True:
        # Find IDs of expired rows (batch)
        expired_ids_q = (
            select(AuditLog.id)
            .where(AuditLog.created_at < cutoff)
            .limit(CLEANUP_BATCH_SIZE)
        )
        result = await db.execute(expired_ids_q)
        ids = [row[0] for row in result.all()]

        if not ids:
            break

        stmt = delete(AuditLog).where(AuditLog.id.in_(ids))
        await db.execute(stmt)
        await db.commit()
        total_deleted += len(ids)

        if len(ids) < CLEANUP_BATCH_SIZE:
            break

    logger.info("Audit log cleanup: deleted %d records older than %s (retention=%d days)",
                total_deleted, cutoff.isoformat(), settings.audit_retention_days)
    return total_deleted
