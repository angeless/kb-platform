# Bridge Service — User Guide (v0.53)

The bridge service synchronizes a local Hogwarts-KB markdown repository
with KBSQL via two protocols:

- **REST API** at `/v1/bridge/*` — for scripts, CI, other agents
- **MCP server** (stdio + streamable-http) — for Claude Code / Desktop

Both protocols share the same underlying logic in
`services/bridge/bridge/`. There is no duplicated business code.

## Quick Start

### Prerequisites

```bash
# 1. Install KBSQL with bridge deps
cd ~/knowledge_SQL
source .venv/bin/activate
pip install -e ./packages/shared-config -e ./packages/shared-models \
            -e ./packages/shared-errors -e ./packages/shared-schemas \
            -e ./packages/bridge-utils \
            -e ./services/bridge -e ./services/api -e ./services/mcp-server

# 2. Configure .env (already done if you ran v0.53 init)
#    Required keys: GLM_API_KEY, HOGWARTS_KB_PATH, HOGWARTS_KB_BRANCH
#    See .env.example for full list.

# 3. (One-time, when going to production) Apply pending DB migrations:
cd infra/sql && alembic upgrade head
```

### Verify configuration

```bash
python -m bridge status
```

Expected output:

```
kb-bridge 0.1.0
  KB path:        /Users/you/Hogwarts-Knowledge-Base
  KB exists:      True
  KB branch:      feature/kbsql-bridge
  Auto-push:      True
  LLM provider:   glm
  LLM strict:     True
  GLM key set:    yes
```

### Start the watcher (long-running)

```bash
python -m bridge watch
```

The watcher monitors `HOGWARTS_KB_PATH/` and dispatches every detected
markdown / office / pdf file change through the parser pipeline.

### One-shot full sync

```bash
python -m bridge sync-once
```

Useful for backfill or after a long downtime.

## REST API

Mounted under `/v1/bridge/*`. All POST endpoints require the
`X-Requested-With: XMLHttpRequest` header (CSRF protection — same as
the rest of KBSQL).

| Method | Path | Purpose |
|--------|------|---------|
| GET    | `/v1/bridge/health`         | Liveness check (no DB) |
| GET    | `/v1/bridge/status`         | Bridge config snapshot |
| POST   | `/v1/bridge/ingest`         | Parse one file, return IR (no DB write) |
| POST   | `/v1/bridge/summarize`      | Local extractive summary |
| POST   | `/v1/bridge/classify`       | Suggest path + tags |
| POST   | `/v1/bridge/write/summary`  | Write summary into wiki/summaries/ + auto-commit |
| POST   | `/v1/bridge/write/analysis` | Write analysis into wiki/analyses/ + auto-commit |
| POST   | `/v1/bridge/sync`           | Trigger full sync (inline in v0.53) |
| GET    | `/v1/bridge/mappings`       | List KB ↔ doc_id mappings (stub in v0.53) |

### curl examples

```bash
# Status
curl http://localhost:8080/v1/bridge/status

# Summarize
curl -X POST http://localhost:8080/v1/bridge/summarize \
  -H "Content-Type: application/json" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d '{"text": "First sentence. Second sentence. Third one.", "target_chars": 100}'

# Write summary
curl -X POST http://localhost:8080/v1/bridge/write/summary \
  -H "Content-Type: application/json" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d '{
    "title": "Test Summary",
    "body": "Body content here.\n",
    "tags": ["test"]
  }'
```

## MCP Server

### Stdio (Claude Code / Desktop)

Configure in your Claude Desktop's `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kbsql-bridge": {
      "command": "/path/to/knowledge_SQL/.venv/bin/python",
      "args": ["-m", "mcp_server"],
      "env": {
        "HOGWARTS_KB_PATH": "/path/to/Hogwarts-Knowledge-Base",
        "GLM_API_KEY": "your-key-here"
      }
    }
  }
}
```

Or for Claude Code, add the same config to `.mcp.json` in your project root.

### Streamable HTTP (remote agents)

```bash
python -m mcp_server --transport streamable-http --host 0.0.0.0 --port 8090
```

Endpoint: `http://your-host:8090/mcp` — this is the modern recommended
transport (replaces SSE). Use the official MCP client library to connect.

### Tools available

| Tool | Description |
|------|-------------|
| `kb_status`         | Bridge config snapshot |
| `kb_search`         | Search KB markdown files (no LLM) |
| `kb_read`           | Read a KB file |
| `kb_ingest`         | Parse a file → IR |
| `kb_summarize`      | Local extractive summary |
| `kb_classify`       | Suggest path + tags |
| `kb_write_summary`  | Write to wiki/summaries/ + auto-commit |
| `kb_write_analysis` | Write to wiki/analyses/ + auto-commit |

## Safety Contract

The bridge enforces these constraints — violations raise errors at runtime:

1. **Path safety**: writes are restricted to `wiki/summaries/` and
   `wiki/analyses/`. Attempts to write `raw-sources/`, `lessons/`,
   `memory/`, or anywhere else are rejected with HTTP 403 / KBWriteError.

2. **Git lock awareness**: bridge waits up to 30s for `.git/index.lock`
   to clear before writing — never overlaps with obsidian-git.

3. **LLM strict mode**: `BRIDGE_LLM_STRICT=true` (default) refuses to
   fall back to OpenAI/Anthropic. Bridge will fail loudly rather than
   silently burn other API quotas.

4. **Source-of-truth contract**: Hogwarts-KB markdown files are
   authoritative. KBSQL DB is a derived cache. On conflict, KB wins.

## Pending Pre-Deployment Tasks

These were identified during v0.53 development but deferred:

1. **Apply pending Alembic migrations** before starting bridge:
   - `y4z5a6b7c8d9` (tenant tier + user org)  — v0.51 leftover
   - `z5a6b7c8d9e0` (stage order + skill + ontology) — v0.51 leftover
   - `a6b7c8d9e0f1` (bridge tables) — v0.53 new

2. **Replace placeholder secrets** in `.env`:
   - `JWT_SECRET=change_me` → `openssl rand -hex 32`
   - `ENCRYPTION_KEY=change_me_32_chars_minimum` → 32-char random

3. **GitHub Dependabot warnings** (6 open: 1 high, 5 moderate) — see
   `https://github.com/angeless/kb-platform/security/dependabot`.

4. **Install heavy ML deps** if you need full multi-format support:
   ```bash
   pip install 'kb-bridge[all]'
   # or selectively:
   pip install docling whisperx scenedetect
   ```

## Architecture

```
Hogwarts-KB (markdown, source of truth)
    │
    │ watchfiles / git events
    ▼
Bridge service (services/bridge/)
    ├── Parsers (markdown_parser, multi_format_parser)
    ├── Watchers (kb_watcher: fs change → IR)
    ├── Writers (kb_writer: IR → wiki/summaries/wiki/analyses + git)
    └── LLM router (Zhipu GLM, strict mode)
        │
        │ shared logic (DRY)
        │
        ├──► REST API (/v1/bridge/*)         ← scripts, CI, agents
        └──► MCP server (stdio | streamable) ← Claude Code, Desktop
```

## Troubleshooting

### "GitLockTimeout: git lock still present"
obsidian-git is mid-commit. Wait or check Obsidian's Git plugin status.
Increase `WRITER_GIT_LOCK_TIMEOUT_S` if your KB is large.

### "BridgeLLMError: BRIDGE_LLM_STRICT=true but BRIDGE_LLM_PROVIDER='openai'"
You changed provider but forgot to set `BRIDGE_LLM_STRICT=false`. This is
a feature, not a bug — bridge refuses to silently use OpenAI in strict mode.

### "ModuleNotFoundError: No module named 'docling'"
The PDF you tried to ingest needs docling. Install with
`pip install docling` (~200MB of ONNX models). The bridge falls back to
markitdown's plain-text PDF reader if docling is missing.

### "CSRF_HEADER_MISSING"
You're hitting the API without `X-Requested-With: XMLHttpRequest`. This
is KBSQL's site-wide CSRF protection — add the header to all POST/PUT/
PATCH/DELETE calls.
