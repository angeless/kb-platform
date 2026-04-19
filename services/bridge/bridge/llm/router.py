"""LLM router with strict-mode safeguard.

Zhipu GLM exposes an OpenAI-compatible API at
https://open.bigmodel.cn/api/paas/v4 — so we use the openai SDK with a
custom base_url and our GLM_API_KEY. This keeps the codebase simple and
swappable.

The strict-mode safeguard refuses to instantiate any non-GLM client when
BRIDGE_LLM_STRICT=true. This prevents accidental fallback to OpenAI/Anthropic
that would burn the user's primary API quotas.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)


class BridgeLLMError(RuntimeError):
    """Raised when bridge LLM router cannot serve a request safely."""


def get_llm_client() -> httpx.AsyncClient:
    """Return an httpx async client preconfigured for the bridge's LLM provider.

    Raises:
        BridgeLLMError: if strict mode is on and provider != 'glm', or if
                        no API key is configured.
    """
    settings = get_settings()

    if settings.bridge_llm_strict and settings.bridge_llm_provider != "glm":
        raise BridgeLLMError(
            f"BRIDGE_LLM_STRICT=true but BRIDGE_LLM_PROVIDER={settings.bridge_llm_provider!r}. "
            "Refusing to use non-GLM provider. Either set BRIDGE_LLM_PROVIDER=glm "
            "or explicitly set BRIDGE_LLM_STRICT=false."
        )

    if settings.bridge_llm_provider == "glm":
        if not settings.glm_api_key:
            raise BridgeLLMError(
                "GLM_API_KEY not configured. Set it in .env or environment."
            )
        return httpx.AsyncClient(
            base_url=settings.bridge_llm_base_url,
            headers={
                "Authorization": f"Bearer {settings.glm_api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    # Other providers explicitly NOT supported in v0.53 even with strict=false.
    # Add support deliberately, not by accident.
    raise BridgeLLMError(
        f"Provider {settings.bridge_llm_provider!r} not implemented in bridge router. "
        "Only 'glm' is supported in v0.53."
    )


async def summarize_with_glm(
    text: str,
    *,
    max_tokens: int = 300,
    temperature: float = 0.3,
    system_prompt: str | None = None,
) -> str:
    """One-shot summarization via GLM (used as fallback when extractive is too noisy).

    This is the ONLY LLM call path for routine bridge operations. Image
    description (kb_writer alt-text) goes through a separate vision endpoint
    helper, also gated by the same router.
    """
    settings = get_settings()
    client = get_llm_client()

    system = system_prompt or (
        "You are a concise technical summarizer. Output Chinese summary "
        "in 200 characters or less. Preserve key entities and numbers. "
        "Do not add commentary."
    )

    payload: dict[str, Any] = {
        "model": settings.bridge_llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text[:8000]},  # GLM-4-flash 8k context
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    async with client:
        resp = await client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
