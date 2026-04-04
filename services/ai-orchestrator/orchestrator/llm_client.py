"""LLM client — calls OpenAI-compatible API via httpx.

Reads configuration from environment variables (shared-config settings).
Does not use the openai SDK to minimize dependencies.
"""

import json
import logging

import httpx

from shared_config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Default model config from env
DEFAULT_API_KEY = getattr(settings, "openai_api_key", "") or ""
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = getattr(settings, "default_model_name", "gpt-4o-mini") or "gpt-4o-mini"


def call_llm(
    prompt: str,
    system_prompt: str = "",
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    timeout: int = 120,
) -> str:
    """Call an OpenAI-compatible chat completion API.

    Returns the assistant's response text.
    Raises RuntimeError on failure.
    """
    key = api_key or DEFAULT_API_KEY
    url = (base_url or DEFAULT_BASE_URL).rstrip("/") + "/chat/completions"
    mdl = model or DEFAULT_MODEL

    if not key:
        raise RuntimeError("No LLM API key configured. Set OPENAI_API_KEY in .env")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": mdl,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    logger.info("Calling LLM: model=%s, prompt_len=%d", mdl, len(prompt))

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise RuntimeError(
            f"LLM API returned {response.status_code}: {response.text[:500]}"
        )

    data = response.json()
    content = data["choices"][0]["message"]["content"]

    # Track token usage and log cost estimate (PRD §5: 成本上限)
    usage = data.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
    logger.info(
        "LLM response: model=%s, chars=%d, tokens=%d (prompt=%d, completion=%d)",
        mdl, len(content), total_tokens, prompt_tokens, completion_tokens,
    )

    # Record usage in CostTracker (v0.52.2 — Gap-16 fix)
    try:
        from .cost_tracker import CostTracker
        _cost_tracker = CostTracker()
        _cost_tracker.record_usage(mdl, prompt_tokens, completion_tokens)
    except Exception as e:
        logger.debug("Cost tracking skipped: %s", e)

    return content


def parse_json_response(text: str) -> dict:
    """Extract and parse JSON from LLM response text.

    Handles cases where the JSON is wrapped in markdown code blocks.
    """
    cleaned = text.strip()

    # Strip markdown code block if present
    if cleaned.startswith("```"):
        # Remove first line (```json or ```)
        lines = cleaned.split("\n")
        lines = lines[1:]  # remove opening ```
        # Remove closing ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e!s}\nResponse: {text[:500]}")
