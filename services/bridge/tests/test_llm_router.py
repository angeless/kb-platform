"""Tests for bridge.llm.router — strict-mode safeguards.

These verify the BRIDGE_LLM_STRICT hard switch actually refuses
non-GLM providers, which is the user's #1 stated security requirement
(don't accidentally burn OpenAI/Anthropic quotas via misconfiguration).
"""

from __future__ import annotations

import pytest

from bridge.llm.router import BridgeLLMError, get_llm_client


def _patch_settings(monkeypatch, **overrides):
    """Helper to inject test BridgeSettings without polluting other tests."""
    from bridge import config as bridge_config
    from bridge.llm import router

    base = {
        "glm_api_key": "test-glm-key",
        "bridge_llm_provider": "glm",
        "bridge_llm_strict": True,
        "bridge_llm_model": "glm-4-flash",
        "bridge_llm_base_url": "https://example.test/v4",
    }
    base.update(overrides)

    class FakeSettings:
        pass

    for k, v in base.items():
        setattr(FakeSettings, k, v)

    monkeypatch.setattr(bridge_config, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(router, "get_settings", lambda: FakeSettings())


def test_get_client_glm_with_key_succeeds(monkeypatch):
    _patch_settings(monkeypatch)
    client = get_llm_client()
    # The async httpx client carries the auth header
    assert "Authorization" in client.headers
    assert "Bearer test-glm-key" in client.headers["Authorization"]
    assert "example.test" in str(client.base_url)


def test_get_client_glm_without_key_raises(monkeypatch):
    _patch_settings(monkeypatch, glm_api_key="")
    with pytest.raises(BridgeLLMError, match="GLM_API_KEY not configured"):
        get_llm_client()


def test_strict_mode_rejects_openai_provider(monkeypatch):
    """The killer test: strict mode + non-GLM provider must FAIL."""
    _patch_settings(monkeypatch, bridge_llm_provider="openai", bridge_llm_strict=True)
    with pytest.raises(BridgeLLMError, match="Refusing to use non-GLM"):
        get_llm_client()


def test_strict_mode_rejects_anthropic_provider(monkeypatch):
    _patch_settings(monkeypatch, bridge_llm_provider="anthropic", bridge_llm_strict=True)
    with pytest.raises(BridgeLLMError, match="Refusing to use non-GLM"):
        get_llm_client()


def test_non_strict_mode_with_unsupported_provider_raises(monkeypatch):
    """Even with strict=false, we don't silently support unimplemented providers."""
    _patch_settings(monkeypatch, bridge_llm_provider="openai", bridge_llm_strict=False)
    with pytest.raises(BridgeLLMError, match="not implemented in bridge router"):
        get_llm_client()


def test_strict_mode_default_is_true(monkeypatch):
    """Sanity: confirm BridgeSettings.bridge_llm_strict defaults to True.

    This is the user's stated security requirement — losing this default
    would silently re-enable OpenAI fallback.
    """
    from bridge.config import BridgeSettings, reset_settings

    monkeypatch.delenv("BRIDGE_LLM_STRICT", raising=False)
    reset_settings()
    s = BridgeSettings()
    assert s.bridge_llm_strict is True
