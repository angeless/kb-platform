"""WebSocket router: real-time job status push via Redis Pub/Sub."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from shared_config.settings import get_settings
from app.utils.security import decode_access_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/v1/ws/jobs/{project_id}")
async def ws_job_status(websocket: WebSocket, project_id: str):
    """Subscribe to real-time job status events for a project.

    Authentication: pass JWT as query parameter `token`.
    Events are published by workers via Redis Pub/Sub.
    """
    # Authenticate via query parameter
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="缺少认证令牌")
        return

    settings = get_settings()
    try:
        payload = decode_access_token(token, settings.jwt_secret, settings.jwt_algorithm)
    except Exception:
        await websocket.close(code=4001, reason="令牌无效或已过期")
        return

    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        await websocket.close(code=4001, reason="令牌缺少租户信息")
        return

    await websocket.accept()

    # Subscribe to Redis channel for this project
    channel_name = f"job_events:{project_id}"

    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel_name)

        logger.info("WebSocket client connected: project=%s tenant=%s", project_id, tenant_id)

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
            await pubsub.unsubscribe(channel_name)
            await redis_client.aclose()
        except Exception:
            pass
