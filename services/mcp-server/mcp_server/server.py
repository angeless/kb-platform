"""MCP server exposing KBSQL bridge tools.

Tools (callable by Claude Code/Desktop):
- kb_status               → bridge configuration snapshot
- kb_search(query)        → search KB markdown files (basename + grep, no LLM)
- kb_read(relative_path)  → return raw markdown content of a KB file
- kb_ingest(path)         → parse a file and return its IR (no DB write)
- kb_summarize(text)      → local extractive summary
- kb_classify(body, ?title)  → suggest path + tags for new content
- kb_write_summary(...)   → write summary into wiki/summaries/ (auto-commit)
- kb_write_analysis(...)  → write analysis into wiki/analyses/ (auto-commit)

All tools share the same underlying logic as the REST endpoints (DRY).

Resources (browseable by clients):
- kb://status                → JSON status snapshot
- kb://files/{relative}      → file content (read-only)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="kbsql-bridge",
    instructions=(
        "KBSQL bridge tools for synchronizing the Hogwarts knowledge base "
        "with KBSQL. Use kb_status to inspect config, kb_search/kb_read to "
        "explore content, and kb_write_summary/kb_write_analysis to publish "
        "AI-generated knowledge back to the KB. All write operations stay "
        "inside wiki/summaries/ or wiki/analyses/ for safety."
    ),
)


# ----- read-only tools --------------------------------------------------------

@mcp.tool()
def kb_status() -> dict[str, Any]:
    """Return current bridge configuration: KB path, branch, LLM provider, etc."""
    from bridge import __version__ as bridge_version
    from bridge.config import get_settings

    s = get_settings()
    return {
        "bridge_version": bridge_version,
        "kb_path": str(s.hogwarts_kb_path),
        "kb_exists": s.hogwarts_kb_path.exists(),
        "kb_branch": s.hogwarts_kb_branch,
        "auto_push": s.hogwarts_kb_auto_push,
        "llm_provider": s.bridge_llm_provider,
        "llm_strict": s.bridge_llm_strict,
        "glm_key_configured": bool(s.glm_api_key),
    }


@mcp.tool()
def kb_search(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search KB markdown files by filename + body grep (case-insensitive, no LLM).

    Args:
        query: search term (substring match)
        max_results: max number of files to return

    Returns:
        List of {relative_path, layer, snippet, match_count}
    """
    from bridge.config import get_settings
    from bridge.parsers.markdown_parser import detect_kb_layer

    s = get_settings()
    if not s.hogwarts_kb_path.exists():
        return []

    q_lower = query.lower()
    results: list[dict[str, Any]] = []

    for path in s.hogwarts_kb_path.rglob("*.md"):
        rel = path.relative_to(s.hogwarts_kb_path)
        rel_str = str(rel)
        if any(rel_str.startswith(p.rstrip("/*")) for p in s.watcher_ignore_globs):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        match_count = content.lower().count(q_lower)
        # Also count filename matches as worth boosting
        name_match = q_lower in rel_str.lower()
        if match_count == 0 and not name_match:
            continue

        # Build a snippet around the first match
        idx = content.lower().find(q_lower)
        if idx >= 0:
            snippet_start = max(0, idx - 60)
            snippet_end = min(len(content), idx + len(query) + 60)
            snippet = content[snippet_start:snippet_end].replace("\n", " ")
        else:
            snippet = content[:120].replace("\n", " ")

        results.append({
            "relative_path": rel_str,
            "layer": detect_kb_layer(path, s.hogwarts_kb_path),
            "snippet": snippet,
            "match_count": match_count + (1 if name_match else 0),
        })

    # Sort by match_count desc, take top N
    results.sort(key=lambda r: r["match_count"], reverse=True)
    return results[:max_results]


@mcp.tool()
def kb_read(relative_path: str) -> dict[str, Any]:
    """Read a KB file's content (markdown or any plain-text file).

    Args:
        relative_path: path relative to KB root, e.g. "wiki/concepts/foo.md"

    Returns:
        {path, content, frontmatter, size_bytes} or {error: "..."}
    """
    from bridge.config import get_settings

    s = get_settings()
    target = (s.hogwarts_kb_path / relative_path).resolve()
    # Path-traversal guard
    try:
        target.relative_to(s.hogwarts_kb_path.resolve())
    except ValueError:
        return {"error": f"Path escapes KB root: {relative_path}"}
    if not target.is_file():
        return {"error": f"File not found: {relative_path}"}

    content = target.read_text(encoding="utf-8", errors="replace")

    # Try to parse frontmatter
    fm: dict[str, Any] = {}
    if relative_path.endswith(".md"):
        try:
            import frontmatter
            post = frontmatter.loads(content)
            fm = dict(post.metadata)
        except Exception:
            pass

    return {
        "path": relative_path,
        "content": content,
        "frontmatter": fm,
        "size_bytes": target.stat().st_size,
    }


@mcp.tool()
def kb_ingest(path: str) -> dict[str, Any]:
    """Parse a file (md or office/pdf/csv/html/etc.) into the bridge IR. No DB write.

    Args:
        path: absolute or KB-relative path

    Returns:
        IR dict (kind, title, content_md, frontmatter, content_hash, ...)
    """
    from bridge.config import get_settings
    from bridge.parsers.markdown_parser import detect_kb_layer, parse_markdown
    from bridge.parsers.multi_format_parser import (
        UnsupportedFormat,
        parse_file,
        supported_extensions,
    )

    s = get_settings()
    p = Path(path)
    if not p.is_absolute():
        p = (s.hogwarts_kb_path / p).resolve()
    if not p.is_file():
        return {"error": f"File not found: {p}"}

    ext = p.suffix.lower()
    try:
        if ext == ".md":
            ir = parse_markdown(p)
        elif ext in supported_extensions():
            ir = parse_file(p)
        else:
            return {"error": f"Unsupported extension: {ext}"}
    except (FileNotFoundError, ValueError, UnsupportedFormat) as e:
        return {"error": str(e)}

    ir["kb_layer"] = detect_kb_layer(p, s.hogwarts_kb_path)
    return ir


@mcp.tool()
def kb_summarize(text: str, target_chars: int = 200, max_sentences: int = 5) -> dict[str, Any]:
    """Local extractive summarization (no LLM). Returns text + confidence."""
    from bridge_utils import summarize_extractive

    res = summarize_extractive(
        text, target_chars=target_chars, max_sentences=max_sentences
    )
    return {
        "text": res.text,
        "sentence_count": res.sentence_count,
        "char_count": res.char_count,
        "confidence": res.confidence,
        "needs_llm_fallback": res.needs_llm_fallback,
        "method": res.method,
    }


@mcp.tool()
def kb_classify(body: str, title_hint: str | None = None) -> dict[str, Any]:
    """Suggest a KB path + tags for a body of markdown."""
    from bridge_utils import classify_path

    sug = classify_path(body, title_hint=title_hint)
    return {
        "page_type": sug.page_type,
        "suggested_path": sug.suggested_path,
        "confidence": sug.confidence,
        "tags": sug.tags,
        "reasoning": sug.reasoning,
    }


# ----- write tools (gated by safety contract in kb_writer) --------------------

@mcp.tool()
def kb_write_summary(
    title: str,
    body: str,
    sources: list[str] | None = None,
    related: list[str] | None = None,
    tags: list[str] | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    """Write a summary into wiki/summaries/ and auto-commit (push if HOGWARTS_KB_AUTO_PUSH=true)."""
    from bridge.writers.kb_writer import (
        GitLockTimeout,
        KBWriteError,
        write_summary_to_kb,
    )

    try:
        return write_summary_to_kb(
            title=title, body=body,
            sources=sources, related=related, tags=tags, slug=slug,
        )
    except (KBWriteError, GitLockTimeout) as e:
        return {"error": str(e), "kind": type(e).__name__}


@mcp.tool()
def kb_write_analysis(
    title: str,
    body: str,
    sources: list[str] | None = None,
    related: list[str] | None = None,
    tags: list[str] | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    """Write an analysis into wiki/analyses/ and auto-commit."""
    from bridge.writers.kb_writer import (
        GitLockTimeout,
        KBWriteError,
        write_analysis_to_kb,
    )

    try:
        return write_analysis_to_kb(
            title=title, body=body,
            sources=sources, related=related, tags=tags, slug=slug,
        )
    except (KBWriteError, GitLockTimeout) as e:
        return {"error": str(e), "kind": type(e).__name__}


# ----- resource: kb://status --------------------------------------------------

@mcp.resource("kb://status")
def kb_status_resource() -> str:
    """Bridge status as a browseable resource (JSON-as-string)."""
    import json
    return json.dumps(kb_status(), indent=2, ensure_ascii=False)


def get_server() -> FastMCP:
    """Return the FastMCP instance. Used by tests + alternative entrypoints."""
    return mcp


# =================================================================
# v0.54 — Graph + Visual augmentation tools
# =================================================================

def _graph_db_path() -> str:
    """Resolve the Kuzu graph DB path from config (deferred env read)."""
    import os as _os
    from bridge.config import get_settings as _gs

    s = _gs()
    default = str(s.hogwarts_kb_path / ".bridge-state" / ".graph.kuzu")
    return _os.environ.get("BRIDGE_GRAPH_DB_PATH", default)


@mcp.tool()
def kb_graph_stats() -> dict[str, Any]:
    """Return current Kuzu graph DB stats: node + relation counts."""
    from bridge_graph import GraphStore

    db = _graph_db_path()
    # Audit S2-H2: context manager releases Kuzu file handle each call
    with GraphStore(db) as gs:
        s = gs.stats()
    return {**{k: int(v) for k, v in s.items()}, "db_path": db}


@mcp.tool()
def kb_graph_neighbors(page_name: str, depth: int = 1) -> list[dict[str, Any]]:
    """Return Pages reachable from `page_name` within `depth` hops (max 5).

    Args:
        page_name: KB-relative path (e.g. 'wiki/concepts/foo')
        depth: 1-5
    """
    from bridge_graph import GraphStore

    with GraphStore(_graph_db_path()) as gs:
        return gs.get_neighbors(page_name, depth=depth)


@mcp.tool()
def kb_graph_pchain(session_id: str) -> list[str]:
    """Trace ancestors of a session_id via parent_session_id (pchain). Newest first."""
    from bridge_graph import GraphStore

    with GraphStore(_graph_db_path()) as gs:
        return gs.get_p_chain(session_id)


@mcp.tool()
def kb_visual_profile(markdown: str) -> dict[str, Any]:
    """Score the human-readability of a markdown article.

    Args:
        markdown: full text (frontmatter included is fine)

    Returns:
        {audience_score, has_steps, has_branches, has_state_machine,
         has_outline_value, heading_count, char_count, rationale}
    """
    from bridge_visual import profile_reader

    p = profile_reader(markdown)
    return {
        "audience_score": p.audience_score,
        "has_steps": p.has_steps,
        "has_branches": p.has_branches,
        "has_state_machine": p.has_state_machine,
        "has_outline_value": p.has_outline_value,
        "heading_count": p.heading_count,
        "char_count": p.char_count,
        "rationale": p.rationale,
    }


@mcp.tool()
def kb_visual_augment(markdown: str, threshold: float | None = None) -> dict[str, Any]:
    """Inject mermaid + outline into markdown when audience_score >= threshold.

    Args:
        markdown: full text (frontmatter included)
        threshold: 0.0-1.0; default = AUDIENCE_HUMAN_THRESHOLD_DEFAULT (0.6)

    Returns:
        {augmented, output, skipped_reason, profile}
    """
    from bridge_visual import (
        AUDIENCE_HUMAN_THRESHOLD_DEFAULT,
        augment_markdown,
    )

    t = threshold if threshold is not None else AUDIENCE_HUMAN_THRESHOLD_DEFAULT
    res = augment_markdown(markdown, threshold=t)
    return {
        "augmented": res.augmented,
        "output": res.output,
        "skipped_reason": res.skipped_reason,
        "profile": {
            "audience_score": res.profile.audience_score,
            "has_steps": res.profile.has_steps,
            "has_branches": res.profile.has_branches,
            "has_state_machine": res.profile.has_state_machine,
            "has_outline_value": res.profile.has_outline_value,
            "heading_count": res.profile.heading_count,
            "char_count": res.profile.char_count,
        },
    }
