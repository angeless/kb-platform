"""Kuzu-backed GraphStore for the KBSQL bridge.

Schema (created idempotently on first connect):

  NODE Page(name STRING PRIMARY KEY, layer STRING, kind STRING,
            session_id STRING, created_at TIMESTAMP)
  NODE Tag(name STRING PRIMARY KEY)
  NODE Episode(session_id STRING PRIMARY KEY,
               parent_session_id STRING, source STRING, recorded_at TIMESTAMP)

  REL references_(FROM Page TO Page,  kind STRING, recorded_at TIMESTAMP)
  REL tagged_with(FROM Page TO Tag,   weight DOUBLE)
  REL produced_in(FROM Page TO Episode)
  REL pchain(FROM Episode TO Episode)  -- parent_session_id link

We use STRING primary keys (not UUIDs) so KB-relative paths can be the
canonical Page identifier ("wiki/concepts/foo"). This makes the graph
trivially queryable from any agent that knows the path.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)


class GraphStoreError(RuntimeError):
    """Raised on graph store operation failures."""


@dataclass(frozen=True)
class Triple:
    """A single (subject, predicate, object) edge to be upserted.

    All identifiers are strings. predicate must be one of the supported
    relation table names (currently: references_, tagged_with, produced_in,
    pchain).
    """

    subject: str
    predicate: str
    object: str
    properties: dict[str, Any] | None = None  # extra edge properties


_REL_TABLES = {"references_", "tagged_with", "produced_in", "pchain"}
_NODE_TABLES = {"Page": "name", "Tag": "name", "Episode": "session_id"}


class GraphStore:
    """Wrapper around a Kuzu DB file.

    Usage:
        gs = GraphStore("/path/to/.graph.kuzu")
        gs.upsert_page("wiki/concepts/foo", layer="wiki", kind="concept",
                       session_id="cc:2026-04-19-foo")
        gs.upsert_triples([Triple("wiki/concepts/foo", "references_",
                                   "wiki/concepts/bar")])
        gs.close()
    """

    def __init__(self, db_path: str | Path):
        try:
            import kuzu  # lazy import
        except ImportError as e:
            raise GraphStoreError(
                "kuzu not installed. Install with: pip install kuzu"
            ) from e

        self._db_path = str(Path(db_path).resolve())
        # Kuzu wants the parent dir to exist
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = kuzu.Database(self._db_path)
        self._conn = kuzu.Connection(self._db)
        self._ensure_schema()

    # ----- schema --------------------------------------------------------

    def _ensure_schema(self) -> None:
        """Create node + relation tables if they don't exist (idempotent)."""
        ddl = [
            "CREATE NODE TABLE IF NOT EXISTS Page("
            "name STRING, layer STRING, kind STRING, "
            "session_id STRING, created_at TIMESTAMP, PRIMARY KEY(name))",
            "CREATE NODE TABLE IF NOT EXISTS Tag(name STRING, PRIMARY KEY(name))",
            "CREATE NODE TABLE IF NOT EXISTS Episode("
            "session_id STRING, parent_session_id STRING, source STRING, "
            "recorded_at TIMESTAMP, PRIMARY KEY(session_id))",
            "CREATE REL TABLE IF NOT EXISTS references_("
            "FROM Page TO Page, kind STRING, recorded_at TIMESTAMP)",
            "CREATE REL TABLE IF NOT EXISTS tagged_with("
            "FROM Page TO Tag, weight DOUBLE)",
            "CREATE REL TABLE IF NOT EXISTS produced_in("
            "FROM Page TO Episode)",
            "CREATE REL TABLE IF NOT EXISTS pchain("
            "FROM Episode TO Episode)",
        ]
        for stmt in ddl:
            self._conn.execute(stmt)

    # ----- mutations -----------------------------------------------------

    def upsert_page(
        self,
        name: str,
        *,
        layer: str = "unknown",
        kind: str = "page",
        session_id: str | None = None,
    ) -> None:
        """Insert or update a Page node by primary key (name)."""
        params = {
            "name": name,
            "layer": layer,
            "kind": kind,
            "session_id": session_id or "",
            "now": datetime.now(timezone.utc),
        }
        # MERGE = "upsert" — Kuzu supports MERGE in 0.4+
        self._conn.execute(
            "MERGE (p:Page {name: $name}) "
            "ON CREATE SET p.layer=$layer, p.kind=$kind, p.session_id=$session_id, p.created_at=$now "
            "ON MATCH  SET p.layer=$layer, p.kind=$kind",
            params,
        )

    def upsert_tag(self, tag: str) -> None:
        self._conn.execute(
            "MERGE (t:Tag {name: $name})",
            {"name": tag},
        )

    def upsert_episode(
        self,
        session_id: str,
        *,
        parent_session_id: str | None = None,
        source: str = "unknown",
    ) -> None:
        params = {
            "sid": session_id,
            "psid": parent_session_id or "",
            "src": source,
            "now": datetime.now(timezone.utc),
        }
        self._conn.execute(
            "MERGE (e:Episode {session_id: $sid}) "
            "ON CREATE SET e.parent_session_id=$psid, e.source=$src, e.recorded_at=$now "
            "ON MATCH  SET e.parent_session_id=$psid, e.source=$src",
            params,
        )
        # If parent_session_id present, also create the pchain edge.
        if parent_session_id:
            self._conn.execute(
                "MERGE (parent:Episode {session_id: $psid}) "
                "ON CREATE SET parent.recorded_at=$now",
                {"psid": parent_session_id, "now": datetime.now(timezone.utc)},
            )
            self._conn.execute(
                "MATCH (a:Episode {session_id: $sid}), (b:Episode {session_id: $psid}) "
                "MERGE (a)-[:pchain]->(b)",
                {"sid": session_id, "psid": parent_session_id},
            )

    def upsert_triples(self, triples: Iterable[Triple]) -> int:
        """Bulk-upsert triples. Returns count actually written."""
        count = 0
        for t in triples:
            if t.predicate not in _REL_TABLES:
                raise GraphStoreError(
                    f"Unknown predicate {t.predicate!r}. "
                    f"Supported: {sorted(_REL_TABLES)}"
                )
            if t.predicate == "references_":
                # Both endpoints must be Pages — auto-upsert if missing
                self.upsert_page(t.subject, kind="page")
                self.upsert_page(t.object, kind="page")
                self._conn.execute(
                    "MATCH (a:Page {name: $s}), (b:Page {name: $o}) "
                    "MERGE (a)-[r:references_]->(b) "
                    "ON CREATE SET r.kind=$k, r.recorded_at=$now",
                    {
                        "s": t.subject,
                        "o": t.object,
                        "k": (t.properties or {}).get("kind", "wiki-link"),
                        "now": datetime.now(timezone.utc),
                    },
                )
            elif t.predicate == "tagged_with":
                self.upsert_page(t.subject, kind="page")
                self.upsert_tag(t.object)
                self._conn.execute(
                    "MATCH (a:Page {name: $s}), (b:Tag {name: $o}) "
                    "MERGE (a)-[r:tagged_with]->(b) "
                    "ON CREATE SET r.weight=$w",
                    {
                        "s": t.subject,
                        "o": t.object,
                        "w": float((t.properties or {}).get("weight", 1.0)),
                    },
                )
            elif t.predicate == "produced_in":
                self.upsert_page(t.subject, kind="page")
                self.upsert_episode(t.object)
                self._conn.execute(
                    "MATCH (a:Page {name: $s}), (b:Episode {session_id: $o}) "
                    "MERGE (a)-[:produced_in]->(b)",
                    {"s": t.subject, "o": t.object},
                )
            count += 1
        return count

    # ----- queries -------------------------------------------------------

    def get_neighbors(self, page_name: str, depth: int = 1) -> list[dict[str, Any]]:
        """Return pages reachable from `page_name` within `depth` hops."""
        depth = max(1, min(depth, 5))  # safety: never run a 100-hop wildcard
        # Kuzu variable-length: -[*1..N]->
        query = (
            f"MATCH (a:Page {{name: $name}})-[r:references_*1..{depth}]->(b:Page) "
            "RETURN DISTINCT b.name AS name, b.layer AS layer, b.kind AS kind"
        )
        res = self._conn.execute(query, {"name": page_name})
        out: list[dict[str, Any]] = []
        while res.has_next():
            row = res.get_next()
            out.append({"name": row[0], "layer": row[1], "kind": row[2]})
        return out

    def get_p_chain(self, session_id: str) -> list[str]:
        """Trace ancestors of a session_id via pchain edges. Newest first."""
        query = (
            "MATCH path = (e:Episode {session_id: $sid})-[:pchain*0..10]->(p:Episode) "
            "RETURN p.session_id"
        )
        res = self._conn.execute(query, {"sid": session_id})
        out = []
        while res.has_next():
            out.append(res.get_next()[0])
        return out

    def stats(self) -> dict[str, int]:
        """Return node + relation counts. Used by /v1/bridge/graph/stats."""
        out: dict[str, int] = {}
        for tbl in _NODE_TABLES:
            res = self._conn.execute(f"MATCH (n:{tbl}) RETURN count(n)")
            out[tbl.lower() + "s"] = res.get_next()[0] if res.has_next() else 0
        for rel in _REL_TABLES:
            res = self._conn.execute(f"MATCH ()-[r:{rel}]->() RETURN count(r)")
            out[rel] = res.get_next()[0] if res.has_next() else 0
        return out

    # ----- lifecycle -----------------------------------------------------

    def ping(self) -> bool:
        """Quick health check."""
        res = self._conn.execute("RETURN 1")
        return res.has_next() and res.get_next()[0] == 1

    def close(self) -> None:
        """Release Kuzu handles."""
        # Kuzu's Python binding doesn't expose a `close` on Connection;
        # garbage collection handles it. Provided for API symmetry.
        del self._conn
        del self._db

    @property
    def db_path(self) -> str:
        return self._db_path
