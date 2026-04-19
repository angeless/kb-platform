"""Hogwarts-KB filesystem watcher (watchfiles, async).

Watches HOGWARTS_KB_PATH for added/modified/deleted files matching the
allowed extensions. For each change:

1. Compute content hash (markdown_parser or multi_format_parser)
2. Look up BridgeSyncRecord by (kb_root, relative_path)
3. If hash matches → no-op (debounce / idempotent)
4. If hash differs → enqueue Celery task `bridge.tasks.bridge_ingest`
5. Append BridgeOperation row

Note: this module is INTENTIONALLY DB-side-effect-free in unit tests —
all DB writes go through `_persist_*` callables that tests can monkeypatch.

The `run_full_sync()` function does the same scan but for ALL files at
startup, useful for backfill.
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
from collections.abc import Awaitable, Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..parsers.markdown_parser import detect_kb_layer, parse_markdown
from ..parsers.multi_format_parser import (
    UnsupportedFormat,
    parse_file,
    supported_extensions,
)

logger = logging.getLogger(__name__)


# File extensions the watcher cares about.
_MD_EXTS = {".md"}


def _get_handled_exts() -> set[str]:
    """Markdown + every multi-format extension we support."""
    return _MD_EXTS | supported_extensions()


def _is_ignored(rel_path: str, ignore_globs: Iterable[str]) -> bool:
    """Check if a relative path matches any glob in the ignore list."""
    for pattern in ignore_globs:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        # Also match directory prefix patterns like ".git/*"
        if pattern.endswith("/*") and rel_path.startswith(pattern[:-2] + "/"):
            return True
    return False


def _classify_and_parse(path: Path, kb_root: Path) -> dict[str, Any] | None:
    """Parse a single file into IR, returning None if unsupported / invalid.

    Returns None instead of raising so the watcher loop doesn't die on one
    bad file. Errors are logged + persisted via BridgeOperation by caller.
    """
    import yaml  # for YAMLError catch (S2-M5 hot-fix from Phase 8 v0.54 audit)

    ext = path.suffix.lower()
    try:
        if ext == ".md":
            ir = parse_markdown(path)
        elif ext in supported_extensions():
            ir = parse_file(path)
        else:
            logger.debug("Skipping unhandled extension: %s", path)
            return None
    except (FileNotFoundError, ValueError, UnsupportedFormat, yaml.YAMLError,
            UnicodeDecodeError) as e:
        # YAMLError catches malformed frontmatter (e.g. duplicate keys, tab indent).
        # UnicodeDecodeError catches files mis-classified as text (e.g. .md
        # symlinks pointing at binary, or Obsidian template files with non-UTF-8 bytes).
        # A single bad file should not crash the watcher / sync loop.
        logger.warning("Parse failed for %s: %s", path, type(e).__name__)
        return None

    ir["kb_layer"] = detect_kb_layer(path, kb_root)
    ir["relative_path"] = str(path.resolve().relative_to(kb_root.resolve()))
    return ir


# ----- async machinery --------------------------------------------------------

async def _process_change(
    path: Path,
    kb_root: Path,
    *,
    persist_fn: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    enqueue_fn: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
) -> dict[str, Any] | None:
    """Process one filesystem change. Returns the IR dict (or None if skipped).

    The persist_fn / enqueue_fn injection lets unit tests verify what the
    watcher would have done without a real DB or Celery broker.
    """
    if not path.is_file():
        # Deletion path — caller should mark BridgeSyncRecord.sync_status='deleted'.
        # That's not handled here; we just return None and let caller decide.
        return None

    ir = _classify_and_parse(path, kb_root)
    if ir is None:
        return None

    if persist_fn is not None:
        await persist_fn(ir)
    if enqueue_fn is not None:
        await enqueue_fn(ir)
    return ir


async def _watch_loop(
    kb_root: Path,
    ignore_globs: Iterable[str],
    *,
    persist_fn: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    enqueue_fn: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    max_iterations: int | None = None,
) -> int:
    """Long-running async watch loop. Returns number of changes processed.

    `max_iterations` exists for testability — pass an int to exit after N
    change batches; default None = forever.
    """
    from watchfiles import Change, awatch  # lazy import

    handled = _get_handled_exts()
    iteration = 0
    total_processed = 0

    logger.info(
        "Watching %s (handled exts: %d, ignore globs: %d)",
        kb_root, len(handled), len(list(ignore_globs)),
    )

    async for changes in awatch(str(kb_root)):
        iteration += 1
        for change_type, path_str in changes:
            path = Path(path_str)
            if path.suffix.lower() not in handled:
                continue
            try:
                rel = path.resolve().relative_to(kb_root.resolve())
            except ValueError:
                continue
            if _is_ignored(str(rel), ignore_globs):
                continue
            if change_type == Change.deleted:
                logger.info("Deleted: %s", rel)
                # Mark as deleted; let persist_fn handle the soft-delete update
                if persist_fn is not None:
                    await persist_fn(
                        {
                            "relative_path": str(rel),
                            "sync_status": "deleted",
                            "content_hash": None,
                            "_deleted_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                total_processed += 1
                continue

            await _process_change(
                path,
                kb_root,
                persist_fn=persist_fn,
                enqueue_fn=enqueue_fn,
            )
            total_processed += 1

        if max_iterations is not None and iteration >= max_iterations:
            break

    return total_processed


def run_watcher() -> int:
    """Synchronous entrypoint for `python -m bridge watch`. Blocks forever.

    NOTE (v0.53 scope boundary): this entrypoint runs the watcher with
    NO persist_fn and NO enqueue_fn injected. That means file changes are
    detected and parsed, but **no DB persistence happens** in v0.53.
    The bridge_ingest Celery stage that writes BridgeSyncRecord rows lands
    in v0.54. A WARNING is emitted on startup so silent operation isn't
    mistaken for success.
    """
    settings = get_settings()
    kb_root = settings.hogwarts_kb_path

    if not kb_root.exists():
        logger.error("KB path does not exist: %s", kb_root)
        return 1

    logger.warning(
        "v0.53 SCOPE BOUNDARY: watcher runs in detect-only mode. "
        "Parsed IRs are discarded; BridgeSyncRecord persistence + Celery "
        "dispatch land in v0.54. Use /v1/bridge/write/* or MCP tools for "
        "explicit write-back in v0.53."
    )

    try:
        asyncio.run(
            _watch_loop(kb_root, settings.watcher_ignore_globs)
        )
    except KeyboardInterrupt:
        logger.info("Watcher stopped by SIGINT")
        return 0
    return 0


def run_full_sync() -> int:
    """One-shot scan of every file in HOGWARTS_KB_PATH.

    v0.54+: actually persists to BridgeSyncRecord via bridge_ingest stage
    when shared-models is importable (i.e. KBSQL DB is reachable). If DB
    not reachable, falls back to detect-only mode + WARNING log.
    """
    settings = get_settings()
    kb_root = settings.hogwarts_kb_path

    if not kb_root.exists():
        logger.error("KB path does not exist: %s", kb_root)
        return 1

    # Propagate .env into os.environ so the downstream bridge_ingest stage
    # (which reads via os.environ.get for BRIDGE_VISUAL_* + BRIDGE_GRAPH_*)
    # sees those values. pydantic-settings loads .env into BridgeSettings
    # but doesn't push into os.environ, so without this load_dotenv call
    # visual augment silently skips. Use override=False to respect any
    # explicit shell-level overrides.
    try:
        from dotenv import load_dotenv as _load
        # Find .env in current dir or parents (matches pydantic-settings behavior)
        from pathlib import Path as _P
        for _p in [_P.cwd(), *_P.cwd().parents]:
            _envf = _p / ".env"
            if _envf.is_file():
                _load(_envf, override=False)
                logger.info("Loaded env vars from %s", _envf)
                break
    except ImportError:
        logger.debug("python-dotenv not installed; relying on shell env only")

    # Try to open a DB session for persistence; gracefully fall back if not reachable
    db_session = None
    bridge_ingest = None
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from shared_config.settings import get_settings as _kbsql_settings
        from worker.stages.bridge_ingest import bridge_ingest as _bi

        kbsql = _kbsql_settings()
        engine = create_engine(kbsql.database_url_sync, future=True)
        SessionLocal = sessionmaker(bind=engine, future=True)
        db_session = SessionLocal()
        bridge_ingest = _bi
        logger.info("Persistence ENABLED (KBSQL DB reachable)")
    except Exception as e:
        logger.warning(
            "Persistence DISABLED — DB unreachable or worker not installed: %s. "
            "Sync will run in detect-only mode (no BridgeSyncRecord rows written).",
            type(e).__name__,
        )

    handled = _get_handled_exts()
    ignore = settings.watcher_ignore_globs
    count = 0
    for path in kb_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in handled:
            continue
        try:
            rel = path.resolve().relative_to(kb_root.resolve())
        except ValueError:
            continue
        if _is_ignored(str(rel), ignore):
            continue
        ir = _classify_and_parse(path, kb_root)
        if ir is None:
            continue
        count += 1
        # Persist via bridge_ingest if DB session opened above
        if db_session is not None and bridge_ingest is not None:
            try:
                bridge_ingest(db_session, ir=ir, kb_root=str(kb_root))
                # Commit per-file so a single bad file doesn't roll back all progress
                db_session.commit()
            except Exception as e:
                db_session.rollback()
                logger.warning("bridge_ingest failed for %s: %s", path, type(e).__name__)
        if count % 50 == 0:
            logger.info("Sync progress: %d files processed", count)

    if db_session is not None:
        db_session.close()
    logger.info("Full sync complete: %d files processed", count)
    return 0
