"""Unit tests for cost_tracker.py — LLM cost tracking."""

from unittest.mock import MagicMock

import importlib.util
import os
import sys

_spec = importlib.util.spec_from_file_location(
    "cost_tracker",
    os.path.join(os.path.dirname(__file__), "..", "orchestrator", "cost_tracker.py"),
)
cost_tracker_mod = importlib.util.module_from_spec(_spec)
sys.modules["cost_tracker_mod"] = cost_tracker_mod
_spec.loader.exec_module(cost_tracker_mod)

CostTracker = cost_tracker_mod.CostTracker


class TestCostTracker:
    def test_record_usage_with_redis(self):
        mock_redis = MagicMock()
        tracker = CostTracker(redis_client=mock_redis)
        tracker.record_usage("gpt-4", 1000, 500)
        assert mock_redis.hincrby.call_count == 2

    def test_check_budget_within_limit(self):
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {b"prompt_tokens": b"100", b"completion_tokens": b"50"}
        tracker = CostTracker(redis_client=mock_redis)
        assert tracker.check_budget("gpt-4", cost_limit_usd=10.0) is True

    def test_check_budget_exceeded(self):
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {b"prompt_tokens": b"500000", b"completion_tokens": b"500000"}
        tracker = CostTracker(redis_client=mock_redis)
        assert tracker.check_budget("gpt-4", cost_limit_usd=0.01) is False

    def test_check_budget_no_limit(self):
        tracker = CostTracker(redis_client=MagicMock())
        assert tracker.check_budget("gpt-4", cost_limit_usd=None) is True

    def test_get_usage_summary(self):
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {b"prompt_tokens": b"1000", b"completion_tokens": b"500"}
        tracker = CostTracker(redis_client=mock_redis)
        summary = tracker.get_usage_summary("gpt-4")
        assert summary["prompt_tokens"] == 1000
        assert summary["completion_tokens"] == 500
        assert summary["cost_usd"] > 0

    def test_redis_unavailable_degrades(self):
        tracker = CostTracker(redis_client=None)
        tracker.record_usage("gpt-4", 100, 50)  # Should not raise
        assert tracker.check_budget("gpt-4", cost_limit_usd=1.0) is True  # Degraded: allow
