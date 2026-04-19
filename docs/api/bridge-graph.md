# Bridge Graph — User Guide (v0.54)

The bridge graph layer adds an **embedded Kuzu graph database** to the
KBSQL bridge service. It indexes entity relationships extracted from your
Hogwarts-KB markdown files (wiki-links, frontmatter `related`/`sources`/
`tags`, session_id → episode), enabling queries that markdown FTS5 alone
can't answer.

> **Why Kuzu, not Neo4j?** Single-file embedded DB (no daemon), MIT license,
> sits next to `.search-index.sqlite` in your KB. Doesn't require a server,
> doesn't lock you in.

## Quick Start

### Install

```bash
cd ~/knowledge_SQL && source .venv/bin/activate
pip install -e ./packages/bridge-graph
# Optional NER mode (Chinese needs zh_core_web_sm; English needs en_core_web_sm)
pip install spacy && python -m spacy download en_core_web_sm
```

### Enable in bridge ingest

```bash
# In your KBSQL .env:
BRIDGE_GRAPH_ENABLED=true
BRIDGE_GRAPH_DB_PATH=/Users/you/Hogwarts-Knowledge-Base/.bridge-state/.graph.kuzu  # default
```

When `BRIDGE_GRAPH_ENABLED=true`, every file processed by `bridge_ingest`
upserts entity/relation triples into the graph DB.

### Ensure `.bridge-state/` is gitignored

Add to your Hogwarts-KB `.gitignore` (already done if you're on
`feature/kbsql-bridge` v0.54+):

```
.bridge-state/
*.kuzu
```

Without this, the Kuzu database files will be committed to git and pushed
to GitHub on the next obsidian-git sync.

## Schema

```
NODE Page(name STRING PK, layer STRING, kind STRING,
          session_id STRING, created_at TIMESTAMP)
NODE Tag(name STRING PK)
NODE Episode(session_id STRING PK, parent_session_id STRING,
             source STRING, recorded_at TIMESTAMP)

REL references_(FROM Page TO Page, kind STRING, recorded_at TIMESTAMP)
REL tagged_with(FROM Page TO Tag, weight DOUBLE)
REL produced_in(FROM Page TO Episode)
REL pchain(FROM Episode TO Episode)  -- parent_session_id link
```

**Page identifiers are KB-relative paths** (e.g. `wiki/concepts/foo`),
not UUIDs. Any agent that knows the path can query the graph directly.

## Python API

```python
from bridge_graph import GraphStore, Triple, extract_triples

# Open / create a graph DB
with GraphStore("/path/to/.graph.kuzu") as gs:
    # Upsert from a parsed bridge IR
    ir = {
        "relative_path": "wiki/concepts/foo.md",
        "wiki_links": ["wiki/concepts/bar"],
        "frontmatter": {
            "tags": ["llm", "vercel"],
            "session_id": "cc:2026-04-19-foo",
        },
        "content_md": "# Foo\n\nSee [[wiki/concepts/bar]].\n",
    }
    triples = extract_triples(ir)
    gs.upsert_triples(triples)

    # Query: what does this page reference?
    neighbors = gs.get_neighbors("wiki/concepts/foo", depth=2)
    for n in neighbors:
        print(n["name"], n["layer"])

    # Query: who are the ancestors of this session?
    chain = gs.get_p_chain("cc:2026-04-19-foo")
    print("session p-chain:", chain)

    # Stats
    print(gs.stats())
```

## REST API

| Method | Path | Purpose |
|--------|------|---------|
| GET    | `/v1/bridge/graph/stats`     | Node + relation counts |
| POST   | `/v1/bridge/graph/neighbors` | Pages reachable from `page_name` within `depth` hops (1-5) |

### curl examples

```bash
# Stats
curl http://localhost:8080/v1/bridge/graph/stats

# Neighbors (note: POST requires X-Requested-With for CSRF)
curl -X POST http://localhost:8080/v1/bridge/graph/neighbors \
  -H "Content-Type: application/json" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d '{"page_name": "wiki/concepts/foo", "depth": 2}'
```

## MCP Tools

For Claude Code/Desktop:

| Tool | Description |
|------|-------------|
| `kb_graph_stats`     | Node + relation counts |
| `kb_graph_neighbors` | Pages reachable within N hops |
| `kb_graph_pchain`    | Session ancestor chain |

## Extraction Modes

`extract_triples(ir, mode=...)`:

- `HEURISTIC` (default) — pure rule-based, ~1ms/file. Wiki-links + frontmatter
  related/sources/tags + session_id. Zero LLM calls.
- `NER_LIGHT` — adds spaCy NER for PERSON/ORG/PRODUCT entities. ~50ms/file.
  Requires `pip install spacy && python -m spacy download <model>`.
- `LLM_DEEP` — placeholder, deferred to v0.55. Will use graphiti-core +
  GLM-4 for relation extraction.

## Performance Notes

- Kuzu 0.11+ supports embedded read+write with WAL. Concurrent writers
  serialize on the file lock; reads can be concurrent.
- The bridge service uses GraphStore in **context manager** form to release
  handles after each REST/MCP call (audit S2-H2).
- Typical KB (1000 files): graph DB is ~10MB on disk, queries < 5ms.
- For very large KBs (> 100k files), consider switching backend to
  FalkorDB or Neo4j (see graphiti-core's BackendAdapter pattern in v0.55).

## Troubleshooting

### `kuzu.Database` raises "Cannot acquire lock"
Another process (e.g. `python -m bridge watch` and your REST API at
the same time) is holding the lock. Either run them in the same process
or stop one.

### Queries return empty even though I have data
1. Verify `BRIDGE_GRAPH_ENABLED=true` in `.env`
2. Run `python -m bridge sync-once` to backfill from existing files
3. Check `BRIDGE_GRAPH_DB_PATH` matches between watcher and queries

### Graph file growing too large
Run `gs._conn.execute("COPY (MATCH (n) RETURN n) TO '/tmp/dump.csv'")`
to extract, then delete the `.kuzu` file and re-sync. The graph is
**rebuildable from KB source** — it's a derived index.

## v0.55 Roadmap

- LLM_DEEP extraction mode (graphiti-core + GLM-4)
- Cypher subset query endpoint (`POST /v1/bridge/graph/query` with whitelist)
- Time-travel queries (`MATCH ... WHERE valid_at < '2026-01-01'`)
- Graph DB read-only mode for high-concurrency reads
