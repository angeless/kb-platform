"""LLM cost tracking with daily budget enforcement.

Stores daily token usage in Redis (key: cost:{route}:{date}).
Checks budget before LLM calls and rejects if exceeded.
"""

import logging
from datetime import date

logger = logging.getLogger(__name__)

# Default price per 1K tokens (USD) — simple model
DEFAULT_PRICES = {
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
    "text-embedding-3-small": {"prompt": 0.00002, "completion": 0.0},
}
DEFAULT_PRICE = {"prompt": 0.01, "completion": 0.03}


class CostTracker:
    """Track LLM token consumption and enforce daily budgets."""

    def __init__(self, redis_client=None):
        self._redis = redis_client

    def _get_redis(self):
        if self._redis:
            return self._redis
        try:
            from shared_config.settings import get_redis_client
            self._redis = get_redis_client()
            return self._redis
        except Exception as e:
            logger.warning("Redis unavailable for cost tracking: %s", e)
            return None

    def record_usage(self, model: str, prompt_tokens: int, completion_tokens: int) -> None:
        """Record token usage for a model on today's date."""
        r = self._get_redis()
        if r is None:
            return

        today = date.today().isoformat()
        key = f"cost:{model}:{today}"
        try:
            r.hincrby(key, "prompt_tokens", prompt_tokens)
            r.hincrby(key, "completion_tokens", completion_tokens)
            r.expire(key, 86400 * 2)  # Auto-expire after 2 days
        except Exception as e:
            logger.warning("Failed to record cost: %s", e)

    def check_budget(self, model: str, cost_limit_usd: float | None = None) -> bool:
        """Check if daily budget allows more LLM calls.

        Returns True if within budget (or no limit set), False if exceeded.
        """
        if cost_limit_usd is None:
            return True

        r = self._get_redis()
        if r is None:
            return True  # Can't check → allow (degraded)

        today = date.today().isoformat()
        key = f"cost:{model}:{today}"
        try:
            data = r.hgetall(key)
            prompt_tokens = int(data.get(b"prompt_tokens", 0))
            completion_tokens = int(data.get(b"completion_tokens", 0))

            prices = DEFAULT_PRICES.get(model, DEFAULT_PRICE)
            cost = (prompt_tokens / 1000 * prices["prompt"] +
                    completion_tokens / 1000 * prices["completion"])

            if cost >= cost_limit_usd:
                logger.warning("Budget exceeded for %s: $%.4f >= $%.4f", model, cost, cost_limit_usd)
                return False
            return True
        except Exception as e:
            logger.warning("Budget check failed: %s", e)
            return True  # Allow on error

    def get_usage_summary(self, model: str) -> dict:
        """Get today's usage summary for a model."""
        r = self._get_redis()
        if r is None:
            return {"prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0}

        today = date.today().isoformat()
        key = f"cost:{model}:{today}"
        try:
            data = r.hgetall(key)
            pt = int(data.get(b"prompt_tokens", 0))
            ct = int(data.get(b"completion_tokens", 0))
            prices = DEFAULT_PRICES.get(model, DEFAULT_PRICE)
            cost = pt / 1000 * prices["prompt"] + ct / 1000 * prices["completion"]
            return {"prompt_tokens": pt, "completion_tokens": ct, "cost_usd": round(cost, 6)}
        except Exception:
            return {"prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0}
