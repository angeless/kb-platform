# Bridge Service — Deployment Guide

## Pre-Deployment Checklist

### 1. Database Migrations (REQUIRED)

Three migrations must be applied in order:

```bash
cd ~/knowledge_SQL/infra/sql
source ../../.venv/bin/activate
alembic upgrade head
```

This applies:
- `y4z5a6b7c8d9` — tenant tier + user org (v0.51 leftover)
- `z5a6b7c8d9e0` — stage order + skill + ontology (v0.51 leftover)
- `a6b7c8d9e0f1` — bridge tables (v0.53 new)

Verify all three landed:

```bash
alembic current
# Expected: a6b7c8d9e0f1 (head)
```

### 2. Secrets Hygiene (REQUIRED)

Rotate all `change_me` placeholders in `.env`:

```bash
JWT_SECRET=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 16)  # 32 hex chars = 32 ASCII chars
```

Confirm `GLM_API_KEY` is set and bridge can hit Zhipu:

```bash
python -c "
import asyncio
from bridge.llm.router import summarize_with_glm
async def t():
    out = await summarize_with_glm('Hello world')
    print('GLM OK:', out[:60])
asyncio.run(t())
"
```

### 3. Hogwarts-KB Configuration

In your local Hogwarts-KB clone, ensure `.bridge-config.yml` exists at
the root. It declares allowed write paths and the ignore list. The
bridge reads this on every operation.

**Enable auto-push to GitHub** (the user's stated goal):

```bash
# In your KBSQL .env:
HOGWARTS_KB_AUTO_PUSH=true
HOGWARTS_KB_BRANCH=main           # or feature/kbsql-bridge during integration
HOGWARTS_KB_REMOTE=https://github.com/your-org/your-kb.git
```

Without `HOGWARTS_KB_AUTO_PUSH=true`, every bridge write commits LOCALLY
but never reaches GitHub. Default is `false` (safer for first-time
testing).

### 3b. NLTK tokenizer data (REQUIRED for summarization)

The local extractive summarizer (`sumy`) needs NLTK punkt data:

```bash
python -c "import nltk; nltk.download('punkt_tab', quiet=True); nltk.download('punkt', quiet=True)"
```

Without this, `POST /v1/bridge/summarize` and `kb_summarize` MCP tool
will raise an NLTK LookupError on first call.

### 3c. v0.54 — Graph layer + visual augmentation (OPTIONAL)

To enable the new v0.54 capabilities:

```bash
# Install the new packages
pip install -e ./packages/bridge-graph -e ./packages/bridge-visual

# In .env:
BRIDGE_GRAPH_ENABLED=true                                 # default: false
BRIDGE_VISUAL_ENABLED=true                                # default: false
BRIDGE_GRAPH_DB_PATH=$HOGWARTS_KB_PATH/.bridge-state/.graph.kuzu  # default
BRIDGE_VISUAL_DRYRUN=false                                # default: false (real write-back)
```

⚠️ **CRITICAL**: Add `.bridge-state/` to your Hogwarts-KB `.gitignore`
BEFORE enabling `BRIDGE_GRAPH_ENABLED=true`. The Kuzu graph file is
derived/rebuildable and should never be committed:

```bash
echo -e ".bridge-state/\n*.kuzu" >> $HOGWARTS_KB_PATH/.gitignore
```

When `BRIDGE_VISUAL_ENABLED=true`, qualifying files (audience_score ≥ 0.6)
get a Mermaid + outline block injected in-place via auto-commit. This
modifies your KB markdown sources. The change is wrapped in
`<!-- bridge-visual:start ... -->` markers so it's idempotent and
reversible.

### 4. Optional: Install heavy parsers

```bash
# Document layout (PDF/scanned/image OCR)
pip install docling

# Audio/video transcription (no LLM)
pip install whisperx faster-whisper scenedetect

# Web pages
pip install playwright readability-lxml
playwright install chromium
```

These are lazy-imported — bridge starts fine without them, but hitting
unsupported formats raises an actionable error.

## Running

### Local development (foreground)

```bash
# Terminal 1: KBSQL API
cd ~/knowledge_SQL && source .venv/bin/activate
cd services/api && uvicorn app.main:create_app --factory --reload --port 8080

# Terminal 2: Bridge watcher
cd ~/knowledge_SQL && source .venv/bin/activate
python -m bridge watch

# Terminal 3 (optional): MCP server for remote agents
python -m mcp_server --transport streamable-http --port 8090
```

### Production (systemd / launchctl example)

`~/Library/LaunchAgents/com.kbsql.bridge-watcher.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.kbsql.bridge-watcher</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/you/knowledge_SQL/.venv/bin/python</string>
    <string>-m</string>
    <string>bridge</string>
    <string>watch</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/you/knowledge_SQL</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOGWARTS_KB_PATH</key>
    <string>/Users/you/Hogwarts-Knowledge-Base</string>
    <key>GLM_API_KEY</key>
    <string>YOUR_KEY</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/kbsql-bridge.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/kbsql-bridge.err</string>
</dict>
</plist>
```

Load with:

```bash
launchctl load ~/Library/LaunchAgents/com.kbsql.bridge-watcher.plist
```

## Monitoring

### Health checks

```bash
# Liveness (no DB)
curl http://localhost:8080/v1/bridge/health

# Config snapshot (DB-free)
curl http://localhost:8080/v1/bridge/status
```

### Operation log (audit trail)

Once Phase 8 (v0.54) wires `BridgeOperation` writes, query via:

```sql
SELECT operation_kind, status, relative_path, duration_ms, created_at
FROM bridge_operation
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC LIMIT 50;
```

## Rollback

If bridge causes issues:

```bash
# 1. Stop the watcher
launchctl unload ~/Library/LaunchAgents/com.kbsql.bridge-watcher.plist

# 2. Roll back the migration
cd infra/sql && alembic downgrade z5a6b7c8d9e0

# 3. Revert the API code
cd ~/knowledge_SQL && git checkout main -- services/api/app/main.py
```

The bridge migration's `downgrade()` cleanly drops all 3 bridge tables.
KBSQL v0.52 functionality is unaffected.

## Capacity / Performance Notes

- Watcher uses watchfiles (Rust-backed) — handles 100k+ files comfortably
- Inline full-sync (v0.53): suitable for KBs < 10k files. For larger
  KBs, dispatch to Celery (v0.54 work item).
- Local summarization (sumy LexRank): ~5ms per 1000 chars on M1.
- markitdown CSV/HTML/docx conversion: 50-200ms per file.
- docling PDF (with layout model): 1-5s per page on CPU.
- Whisper transcription: roughly 0.5x real-time on CPU for `large-v3`.
