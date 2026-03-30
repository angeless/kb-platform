"""WebSocket router: real-time job status push via Redis Pub/Sub."""

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import get_settings
from shared_models import Project
from app.deps import get_db
from app.utils.security import decode_access_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/v1/ws/jobs/{project_id}")
async def ws_job_status(websocket: WebSocket, project_id: str):
    """Subscribe to real-time job status events for a project.

    Authentication: JWT from httpOnly cookie (secure, not exposed in URL/logs).
    Tenant isolation: verifies project_id belongs to the JWT's tenant.
    Events are published by workers via Redis Pub/Sub.
    """
    # Authenticate via httpOnly cookie (H-03 fix: no longer via URL query param)
    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=4001, reason="缺少认证令牌")
        return

    settings = get_settings()
    try:
        payload = decode_access_token(token, settings.jwt_secret, settings.jwt_algorithm)
    except Exception:
        await websocket.close(code=4001, reason="令牌无效或已过期")
        return

    kb_id = payload.get("kb_id")
    if not kb_id:
        await websocket.close(code=4001, reason="令牌缺少租户信息")
        return

    # Tenant isolation: verify project belongs to this tenant
    try:
        project_uuid = uuid.UUID(project_id)
        tenant_uuid = uuid.UUID(kb_id)
    except ValueError:
        await websocket.close(code=4003, reason="项目ID格式无效")
        return

    # Use a dedicated DB session for the WebSocket connection
    from shared_models.database import async_session_factory
    async with async_session_factory() as db:
        result = await db.execute(
            select(Project.id).where(
                Project.id == project_uuid,
                Project.kb_id == tenant_uuid,
            )
        )
        if result.scalar_one_or_none() is None:
            await websocket.close(code=4003, reason="项目不存在或无权访问")
            return

    await websocket.accept()

    # Subscribe to Redis channel for this project
    channel_name = f"job_events:{project_id}"

    redis_client = None
    pubsub = None
    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel_name)

        logger.info("WebSocket client connected: project=%s tenant=%s", project_id, kb_id)

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                await websocket.send_text(message["data"])

            # Small sleep to prevent busy loop
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected: project=%s", project_id)
    except Exception as e:
        logger.warning("WebSocket error: %s", e)
    finally:
        try:
            if pubsub is not None:
                await pubsub.unsubscribe(channel_name)
            if redis_client is not None:
                await redis_client.aclose()
        except Exception:
            pass
