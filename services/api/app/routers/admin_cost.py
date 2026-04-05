"""Admin cost summary endpoint — reads daily LLM usage from Redis."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from shared_schemas.common import DataResponse, ErrorDetail

from app.deps import require_role
from shared_models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/admin", tags=["admin"])


class CostSummaryItem(BaseModel):
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


@router.get(
    "/cost-summary",
    response_model=DataResponse[list[CostSummaryItem]],
    summary="Get today's LLM cost summary",
    responses={
        401: {"description": "Unauthorized", "model": ErrorDetail},
        403: {"description": "Forbidden — requires tenant_admin role", "model": ErrorDetail},
    },
)
async def get_cost_summary(
    _user: User = require_role("tenant_admin"),
):
    """Read today's cost data from Redis for all known models."""
    from datetime import date

    try:
        from shared_config.settings import get_async_redis_client
        r = get_async_redis_client()
    except Exception as e:
        logger.warning("Redis unavailable for cost summary: %s", e)
        return DataResponse(data=[])

    today = date.today().isoformat()
    models = ["gpt-4", "gpt-4o", "gpt-3.5-turbo", "text-embedding-3-small"]

    # Price table (same as cost_tracker.py)
    prices = {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-4o": {"prompt": 0.005, "completion": 0.015},
        "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
        "text-embedding-3-small": {"prompt": 0.00002, "completion": 0.0},
    }

    results = []
    try:
        for model in models:
            key = f"cost:{model}:{today}"
            try:
                data = await r.hgetall(key)
                if not data:
                    continue
                pt = int(data.get(b"prompt_tokens", 0))
                ct = int(data.get(b"completion_tokens", 0))
                p = prices.get(model, {"prompt": 0.01, "completion": 0.03})
                cost = pt / 1000 * p["prompt"] + ct / 1000 * p["completion"]
                results.append(CostSummaryItem(
                    model=model,
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    cost_usd=round(cost, 6),
                ))
            except Exception as e:
                logger.warning("Failed to read cost for model %s: %s", model, e)
                continue
    finally:
        try:
            await r.aclose()
        except Exception:
            logger.warning("Failed to close Redis connection in cost summary")

    return DataResponse(data=results)
