"""MCP server entrypoint.

Examples:
    python -m mcp_server                                # stdio (default)
    python -m mcp_server --transport stdio
    python -m mcp_server --transport streamable-http --port 8090
"""

from __future__ import annotations

import argparse
import logging
import sys

from .server import mcp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mcp_server", description="KBSQL bridge MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="MCP transport (default: stdio for Claude Desktop / Claude Code)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host (streamable-http only)")
    parser.add_argument("--port", type=int, default=8090, help="HTTP port (streamable-http only)")
    parser.add_argument("--log-level", default="INFO", help="Log level (DEBUG/INFO/WARNING/ERROR)")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.transport == "streamable-http":
        # FastMCP picks up host/port from the constructor; set them on the instance
        mcp.settings.host = args.host
        mcp.settings.port = args.port

    mcp.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    sys.exit(main())
