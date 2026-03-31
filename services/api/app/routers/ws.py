"""WebSocket router: real-time job status push via Redis Pub/Sub."""

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from shared_config.settings import get_settings
from shared_errors import ForbiddenException, UnauthorizedException
from shared_models import Project
from app.services.pass_client import PassClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/v1/ws/jobs/{project_id}")
async def ws_job_status(websocket: WebSocket, project_id: str):
    """Subscribe to real-time job status events for a project.

    Authentication: Pass JWT from httpOnly cookie verified via Pass /me.
    Tenant isolation: verifies project_id belongs to the user's tenant.
    Events are published by workers via Redis Pub/Sub.
    """
    # Authenticate via httpOnly cookie → Pass /me
    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=4001, reason="缺少认证令牌")
        return

    settings = get_settings()
    pass_client = PassClient(settings)
    try:
        pass_info = await pass_client.me(token)
    except UnauthorizedException:
        await websocket.close(code=4001, reason="令牌无效或已过期")
        return
    except ForbiddenException:
        await websocket.close(code=4003, reason="账号已被封禁")
        return
    except Exception as e:
        logger.error("WebSocket auth: Pass service error: %s", e)
        await websocket.close(code=4002, reason="认证服务暂时不可用")
        return

    pass_id = pass_info.get("passId")
    if not pass_id:
        await websocket.close(code=4001, reason="令牌缺少用户信息")
        return

    # Look up KB User by pass_id to get kb_id for tenant isolation
    from shared_models import User
    from shared_models.database import async_session_factory

    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.pass_id == pass_id))
        user = result.scalar_one_or_none()
        if user is None:
            await websocket.close(code=4001, reason="用户未注册")
            return
        kb_id = user.kb_id

    # Tenant isolation: verify project belongs to this tenant
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        await websocket.close(code=4003, reason="项目ID格式无效")
        return

    async with async_session_factory() as db:
        result = await db.execute(
            select(Project.id).where(
                Project.id == project_uuid,
                Project.kb_id == kb_id,
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

        logger.info("WebSocket client connected: project=%s kb_id=%s", project_id, kb_id)

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                await websocket.send_text(message["data"])

            # Small sleep to prevent busy loop
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected: project=%s", project_id)
    except Exception as e:
        logger.error("WebSocket error: project=%s", project_id, exc_info=True)
    finally:
        try:
            if pubsub is not None:
                await pubsub.unsubscribe(channel_name)
            if redis_client is not None:
                await redis_client.aclose()
        except Exception as e:
            logger.debug("WebSocket cleanup error: %s", e)
