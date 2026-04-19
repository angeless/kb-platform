"""Bridge LLM router (Zhipu GLM, OpenAI-compatible).

ALL LLM calls in the bridge MUST go through router.get_llm_client(). The router
enforces BRIDGE_LLM_STRICT — a hard refusal to fall back to OpenAI/Anthropic
even if the bridge is misconfigured. This protects the user's other API
quotas during a runaway ingestion.
"""

from .router import get_llm_client, summarize_with_glm, BridgeLLMError

__all__ = ["get_llm_client", "summarize_with_glm", "BridgeLLMError"]
