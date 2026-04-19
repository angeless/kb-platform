"""KBSQL ↔ Hogwarts-KB bidirectional bridge service.

This package contains the core bridge runtime that:
- Watches the local Hogwarts-KB markdown filesystem (kb_watcher)
- Parses incoming files and queues KBSQL ingestion (parsers)
- Writes KBSQL processing results back into KB (writers)
- Maintains sync state via three new SQLAlchemy models (BridgeSyncRecord,
  BridgeMapping, BridgeOperation) — see packages/shared-models/

Two protocols expose bridge functionality:
- REST API:    services/api/app/routers/bridge.py  (for scripts / other agents)
- MCP server:  services/mcp-server/                 (for Claude Code / Desktop)

Both reuse the same underlying bridge package — never duplicate logic.

Bridge LLM router uses Zhipu GLM exclusively. The hard switch
BRIDGE_LLM_STRICT=true (default) refuses fallback to OpenAI/Anthropic
even if BRIDGE_LLM_PROVIDER is misconfigured. See bridge/llm/router.py.

Source-of-truth contract:
- Hogwarts-KB markdown files = SOURCE OF TRUTH
- KBSQL DB                    = derived cache (rebuildable from KB)
- Conflicts always resolved in favor of KB
"""

__version__ = "0.1.0"
