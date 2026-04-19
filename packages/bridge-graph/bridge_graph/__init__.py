"""bridge-graph — embedded graph layer for KBSQL bridge.

Stores entity/relation triples extracted from Hogwarts-KB markdown into a
single-file Kuzu database. Schema-first (Page nodes + typed relations) for
fast queries and predictable storage.

Design decisions:

- Kuzu over Neo4j: single embeddable file, no daemon, fits the
  "vault-adjacent file like .search-index.sqlite" model.
- Schema-first nodes/relations: Kuzu requires CREATE TABLE upfront. We use
  a fixed minimal schema (Page + 4 relation types) — sufficient for KB
  navigation; extension is via JSON properties on edges, not new tables.
- Local-only extraction by default: spaCy NER + wiki-link heuristics
  produce most edges. Optional graphiti-core / GLM integration is gated
  behind feature flags (BRIDGE_GRAPH_LLM_ENABLED).
- session_id as episode id: each upsert call is one "episode" identified
  by the source's session_id, making p-chain queries possible
  (`MATCH (e:Episode {parent_session_id: ...}) ...`).
"""

from .store import GraphStore, Triple, GraphStoreError
from .extract import extract_triples, ExtractionMode

__version__ = "0.1.0"
__all__ = [
    "GraphStore",
    "Triple",
    "GraphStoreError",
    "extract_triples",
    "ExtractionMode",
]
