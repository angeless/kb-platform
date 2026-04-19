"""Markdown parser — extracts frontmatter, body, wiki-links, URLs from .md files.

Hogwarts-KB markdown convention (per ~/Hogwarts-Knowledge-Base/SCHEMA.md):
- raw-sources/  — frontmatter required: title, source, date_added, added_by, tags
- wiki/         — frontmatter required: title, type, created, updated, updated_by, sources, related, tags
- lessons/      — frontmatter required: title, date, author, context, tags
- memory/       — frontmatter required: session_id, parent_session_id, source

Wiki-links use Obsidian syntax: [[wiki/concepts/page]] or [[concepts/page]].
External URLs are detected via standard markdown link syntax + bare URL regex.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import frontmatter

# Obsidian-style wiki link: [[target]] or [[target|alias]]
_WIKI_LINK_RE = re.compile(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]")

# Markdown link: [text](url)
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

# Bare URL: http(s)://...
_BARE_URL_RE = re.compile(r"https?://[^\s<>\"')]+")


def _extract_wiki_links(body: str) -> list[str]:
    """Find all [[wiki/...]] references. Deduped, order-preserving."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _WIKI_LINK_RE.finditer(body):
        target = m.group(1).strip()
        if target and target not in seen:
            seen.add(target)
            out.append(target)
    return out


def _extract_outbound_urls(body: str) -> list[str]:
    """Find all external http(s) URLs in body (markdown links + bare). Deduped."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _MD_LINK_RE.finditer(body):
        url = m.group(1).strip()
        if url.startswith(("http://", "https://")) and url not in seen:
            seen.add(url)
            out.append(url)
    for m in _BARE_URL_RE.finditer(body):
        url = m.group(0).rstrip(".,;:)")
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def _derive_title(meta: dict[str, Any], body: str, source_path: Path) -> str:
    """Title from frontmatter > first H1 > filename stem."""
    if isinstance(meta.get("title"), str) and meta["title"].strip():
        return meta["title"].strip()
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line:  # first non-empty line was not H1; stop scanning
            break
    return source_path.stem


def parse_markdown(path: str | Path) -> dict[str, Any]:
    """Parse a markdown file into the canonical bridge IR.

    Args:
        path: Path to the .md file.

    Returns:
        IR dict (see bridge/parsers/__init__.py docstring for schema).

    Raises:
        FileNotFoundError: if path doesn't exist.
        ValueError: if file is empty or not utf-8 decodable.
    """
    p = Path(path).resolve()
    if not p.is_file():
        raise FileNotFoundError(f"Not a file: {p}")

    raw_bytes = p.read_bytes()
    if not raw_bytes:
        raise ValueError(f"Empty file: {p}")

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"File not UTF-8: {p}") from e

    post = frontmatter.loads(text)
    meta: dict[str, Any] = dict(post.metadata)
    body: str = post.content or ""

    # Canonical content_md = body with stripped trailing whitespace, normalized newlines.
    canonical = body.replace("\r\n", "\n").rstrip() + "\n"

    return {
        "kind": "markdown",
        "title": _derive_title(meta, canonical, p),
        "content_md": canonical,
        "frontmatter": meta,
        "wiki_links": _extract_wiki_links(canonical),
        "outbound_urls": _extract_outbound_urls(canonical),
        "raw_size": len(raw_bytes),
        "content_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "source_path": str(p),
        "source_format": "md",
    }


def detect_kb_layer(source_path: str | Path, kb_root: str | Path) -> str:
    """Classify which Hogwarts-KB layer a file belongs to.

    Returns one of: 'raw-sources', 'wiki', 'lessons', 'memory', 'unknown'.
    """
    sp = Path(source_path).resolve()
    root = Path(kb_root).resolve()
    try:
        rel = sp.relative_to(root)
    except ValueError:
        return "unknown"
    top = rel.parts[0] if rel.parts else ""
    if top in {"raw-sources", "wiki", "lessons", "memory"}:
        return top
    return "unknown"
