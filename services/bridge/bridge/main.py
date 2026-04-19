"""Bridge service entrypoint.

Usage:
    python -m bridge --version
    python -m bridge watch     # start fs watcher (long-running)
    python -m bridge sync-once # one-shot full sync of HOGWARTS_KB_PATH
    python -m bridge status    # print current sync state
"""

from __future__ import annotations

import argparse
import logging
import sys

from . import __version__
from .config import get_settings

logger = logging.getLogger(__name__)


def cmd_version(_args: argparse.Namespace) -> int:
    print(f"kb-bridge {__version__}")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    settings = get_settings()
    print(f"kb-bridge {__version__}")
    print(f"  KB path:        {settings.hogwarts_kb_path}")
    print(f"  KB exists:      {settings.hogwarts_kb_path.exists()}")
    print(f"  KB branch:      {settings.hogwarts_kb_branch}")
    print(f"  Auto-push:      {settings.hogwarts_kb_auto_push}")
    print(f"  LLM provider:   {settings.bridge_llm_provider}")
    print(f"  LLM strict:     {settings.bridge_llm_strict}")
    print(f"  GLM key set:    {'yes' if settings.glm_api_key else 'NO (bridge will fail on LLM ops)'}")
    return 0


def cmd_watch(_args: argparse.Namespace) -> int:
    """Start the long-running fs watcher.

    Implementation lives in bridge.watchers.kb_watcher (added in v0.53.3).
    This entrypoint just imports and runs it.
    """
    from .watchers.kb_watcher import run_watcher  # lazy import

    settings = get_settings()
    logger.info("Starting bridge watcher on %s", settings.hogwarts_kb_path)
    return run_watcher()


def cmd_sync_once(_args: argparse.Namespace) -> int:
    """One-shot sync — useful for backfill or after long downtime."""
    from .watchers.kb_watcher import run_full_sync  # lazy import

    settings = get_settings()
    logger.info("Running one-shot sync on %s", settings.hogwarts_kb_path)
    return run_full_sync()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bridge", description="KBSQL ↔ Hogwarts-KB bridge")
    parser.add_argument("--version", action="version", version=f"kb-bridge {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=False)

    sub.add_parser("status", help="Show bridge configuration and sync state")
    sub.add_parser("watch", help="Start filesystem watcher (long-running)")
    sub.add_parser("sync-once", help="Run a one-shot full sync of HOGWARTS_KB_PATH")
    sub.add_parser("version", help="Print version and exit")

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    parser = build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "version": cmd_version,
        "status": cmd_status,
        "watch": cmd_watch,
        "sync-once": cmd_sync_once,
    }
    handler = handlers.get(args.cmd or "status")  # default = status
    if handler is None:
        parser.print_help()
        return 2
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
