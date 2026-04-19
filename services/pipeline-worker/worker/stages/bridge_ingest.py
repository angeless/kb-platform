"""Stage 0: bridge_ingest — KB markdown file → BridgeSyncRecord (+ optional graph).

This is the v0.54 implementation of the v0.53 ADR-002 deferred stage.
Runs BEFORE the classify stage. Triggered by:
  - bridge.watchers.kb_watcher detecting a file change (Celery enqueue)
  - explicit POST /v1/bridge/sync (full re-scan)
  - explicit POST /v1/bridge/ingest (single file)

Behavior:
  1. Persist/update BridgeSyncRecord (path, hash, layer, status)
  2. If hash unchanged vs DB → no-op (idempotent dedupe)
  3. If BRIDGE_GRAPH_ENABLED → extract triples + upsert into Kuzu graph
  4. If BRIDGE_VISUAL_ENABLED → run augmenter, return suggested KB write-back
     (does NOT write back automatically — caller decides)

Side effects: writes to bridge_sync_record + bridge_operation tables
(+ optional .graph.kuzu file if graph enabled). NEVER modifies KB
markdown files directly — that's kb_writer's job, with explicit calls.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared_models import BridgeOperation, BridgeSyncRecord

logger = logging.getLogger(__name__)


def bridge_ingest(
    db: Session,
    *,
    ir: dict[str, Any],
    kb_root: str,
    enable_graph: bool | None = None,
    enable_visual: bool | None = None,
) -> dict[str, Any]:
    """Process one bridge IR through the v0.54 ingest pipeline.

    Args:
        db: SQLAlchemy session (caller manages commit/rollback)
        ir: bridge IR dict from bridge.parsers.{markdown,multi_format}
            Required keys: relative_path, content_hash, source_format, raw_size
            Optional: kb_layer (default 'unknown'), frontmatter, content_md
        kb_root: absolute path to the KB root (HOGWARTS_KB_PATH at sync time)
        enable_graph: if None, read BRIDGE_GRAPH_ENABLED env (default false)
        enable_visual: if None, read BRIDGE_VISUAL_ENABLED env (default false)

    Returns:
        {
            "status": "created" | "updated" | "unchanged" | "error",
            "sync_record_id": str | None,
            "graph_triples_upserted": int,
            "visual_augmented": bool,
            "duration_ms": int,
        }
    """
    started = time.monotonic()
    rel = ir.get("relative_path")
    if not rel:
        raise ValueError("ir missing relative_path")

    enable_graph = (
        enable_graph
        if enable_graph is not None
        else os.environ.get("BRIDGE_GRAPH_ENABLED", "false").lower() == "true"
    )
    enable_visual = (
        enable_visual
        if enable_visual is not None
        else os.environ.get("BRIDGE_VISUAL_ENABLED", "false").lower() == "true"
    )

    # 1) Upsert BridgeSyncRecord
    existing = db.execute(
        select(BridgeSyncRecord).where(
            BridgeSyncRecord.kb_root == kb_root,
            BridgeSyncRecord.relative_path == rel,
        )
    ).scalar_one_or_none()

    new_hash = ir.get("content_hash")
    layer = ir.get("kb_layer", "unknown")
    fmt = ir.get("source_format")
    size = ir.get("raw_size")
    now = datetime.now(timezone.utc)

    if existing is None:
        existing = BridgeSyncRecord(
            kb_root=kb_root,
            relative_path=rel,
            kb_layer=layer,
            content_hash=new_hash,
            file_size_bytes=size,
            source_format=fmt,
            sync_status="parsed",
            last_kb_mtime=now,
        )
        db.add(existing)
        status = "created"
    elif existing.content_hash == new_hash:
        status = "unchanged"
    else:
        existing.content_hash = new_hash
        existing.kb_layer = layer
        existing.file_size_bytes = size
        existing.source_format = fmt
        existing.sync_status = "parsed"
        existing.last_kb_mtime = now
        existing.last_error = None
        status = "updated"
    db.flush()  # populate existing.id without committing

    # 2) Optional: graph upsert
    triples_count = 0
    if enable_graph and status != "unchanged":
        try:
            from bridge_graph import GraphStore, extract_triples

            db_path = os.environ.get(
                "BRIDGE_GRAPH_DB_PATH",
                os.path.join(kb_root, ".bridge-state", ".graph.kuzu"),
            )
            gs = GraphStore(db_path)
            sid = (ir.get("frontmatter") or {}).get("session_id")
            if sid:
                psid = (ir.get("frontmatter") or {}).get("parent_session_id")
                src = (ir.get("frontmatter") or {}).get("source", "unknown")
                gs.upsert_episode(sid, parent_session_id=psid, source=src)
            triples = extract_triples(ir)
            triples_count = gs.upsert_triples(triples)
        except Exception as e:
            logger.warning("graph upsert failed for %s: %s", rel, e)

    # 3) Optional: visual augmentation
    #    By default writes the augmented result back IN-PLACE to the source
    #    file (per user goal "在收入库的同时也为文章内容增加流程图").
    #    Set BRIDGE_VISUAL_DRYRUN=true to skip the write-back.
    visual_augmented = False
    visual_written_back = False
    if enable_visual and status != "unchanged" and ir.get("content_md"):
        try:
            import frontmatter as _fm

            from bridge_visual import augment_markdown

            # Reconstruct full source (frontmatter + body) so the augmenter's
            # reader profiler sees `type:`, `tags:` etc. for accurate scoring.
            fm_dict = ir.get("frontmatter") or {}
            full_md = _fm.dumps(_fm.Post(ir["content_md"], **fm_dict)) + "\n"
            res = augment_markdown(full_md)
            visual_augmented = res.augmented

            # Auto write-back unless dry-run mode or content didn't actually change
            dryrun = os.environ.get("BRIDGE_VISUAL_DRYRUN", "false").lower() == "true"
            if visual_augmented and not dryrun:
                from bridge.writers import augment_existing_in_place

                try:
                    write_res = augment_existing_in_place(
                        relative_path=rel,
                        augmented_full_text=res.output,
                    )
                    visual_written_back = not write_res.get("skipped", False)
                except Exception as wb_err:
                    # Don't fail the whole ingest if write-back fails — log
                    # the issue (visible in BridgeOperation.detail) and continue
                    logger.warning("visual write-back failed for %s: %s", rel, wb_err)
        except Exception as e:
            logger.warning("visual augment failed for %s: %s", rel, e)

    # 4) Append operation log
    duration_ms = int((time.monotonic() - started) * 1000)
    db.add(
        BridgeOperation(
            operation_kind="bridge_ingest",
            status="ok" if status != "error" else "error",
            kb_root=kb_root,
            relative_path=rel,
            detail={
                "outcome": status,
                "graph_enabled": enable_graph,
                "visual_enabled": enable_visual,
                "triples_upserted": triples_count,
                "visual_augmented": visual_augmented,
                "visual_written_back": visual_written_back,
            },
            duration_ms=duration_ms,
        )
    )

    return {
        "status": status,
        "sync_record_id": str(existing.id),
        "graph_triples_upserted": triples_count,
        "visual_augmented": visual_augmented,
        "visual_written_back": visual_written_back,
        "duration_ms": duration_ms,
    }
