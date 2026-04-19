"""MCP server for KBSQL bridge.

Exposes KB sync + summarize + classify tools to MCP clients like Claude Code
and Claude Desktop. Two transport modes:

- stdio: launch as subprocess (typical for Claude Desktop / Claude Code)
- streamable-http: long-running HTTP service (for remote agents)

Entrypoints:
    python -m mcp_server                       # stdio mode (default)
    python -m mcp_server --transport streamable-http --port 8090
"""

__version__ = "0.1.0"
