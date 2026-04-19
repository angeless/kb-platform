"""REST API endpoints for the KBSQL ↔ Hogwarts-KB bridge service.

These endpoints are the script-friendly / non-MCP entrypoint to bridge
functionality. The same operations are also exposed via MCP server
(services/mcp-server/) for Claude Code/Desktop agents.

Endpoint inventory:
  GET  /v1/bridge/status        — bridge config, KB path, last sync time
  GET  /v1/bridge/health        — quick liveness check (no DB)
  POST /v1/bridge/sync          — trigger a one-shot full sync
  POST /v1/bridge/ingest        — parse a single file path and queue it
  POST /v1/bridge/summarize     — return extractive summary (no LLM)
  POST /v1/bridge/classify      — return path/tag suggestions
  POST /v1/bridge/write/summary — write a summary back to KB (auto-commit)
  POST /v1/bridge/write/analysis — write an analysis back to KB
  GET  /v1/bridge/mappings      — list KB path ↔ doc_id mappings (paginated)

All write endpoints are admin-only (TODO: enforce via middleware).
v0.53 ships with admin-by-default semantics; v0.54 will add explicit RBAC.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/bridge", tags=["bridge"])


# ----- request/response models ------------------------------------------------

class BridgeStatusResponse(BaseModel):
    bridge_version: str
    kb_path: str
    kb_exists: bool
    kb_branch: str
    auto_push: bool
    llm_provider: str
    llm_strict: bool
    glm_key_configured: bool


class IngestRequest(BaseModel):
    path: str = Field(..., description="Absolute path or path relative to KB root")


class IngestResponse(BaseModel):
    relative_path: str
    kind: str
    kb_layer: str
    content_hash: str
    raw_size: int


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target_chars: int = Field(default=200, ge=50, le=2000)
    max_sentences: int = Field(default=5, ge=1, le=20)


class SummarizeResponse(BaseModel):
    text: str
    sentence_count: int
    char_count: int
    confidence: float
    needs_llm_fallback: bool
    method: str


class ClassifyRequest(BaseModel):
    body: str = Field(..., min_length=1)
    title_hint: str | None = None


class ClassifyResponse(BaseModel):
    page_type: str
    suggested_path: str
    confidence: float
    tags: list[str]
    reasoning: list[str]


class WriteSummaryRequest(BaseModel):
    title: str
    body: str
    sources: list[str] | None = None
    related: list[str] | None = None
    tags: list[str] | None = None
    slug: str | None = None


class WriteResponse(BaseModel):
    path: str
    commit_sha: str
    wrote_bytes: int
    auto_pushed: bool


# ----- endpoints --------------------------------------------------------------

@router.get(
    "/health",
    summary="Bridge liveness check",
    description="Returns 200 if bridge module imports OK. No DB / KB access.",
)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/status",
    response_model=BridgeStatusResponse,
    summary="Bridge configuration + KB sync state",
)
async def status_endpoint() -> BridgeStatusResponse:
    from bridge import __version__ as bridge_version
    from bridge.config import get_settings

    s = get_settings()
    return BridgeStatusResponse(
        bridge_version=bridge_version,
        kb_path=str(s.hogwarts_kb_path),
        kb_exists=s.hogwarts_kb_path.exists(),
        kb_branch=s.hogwarts_kb_branch,
        auto_push=s.hogwarts_kb_auto_push,
        llm_provider=s.bridge_llm_provider,
        llm_strict=s.bridge_llm_strict,
        glm_key_configured=bool(s.glm_api_key),
    )


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Parse a single file (no DB write)",
    description="Useful for previewing what bridge would store before triggering a full sync.",
)
async def ingest(req: IngestRequest) -> IngestResponse:
    from bridge.config import get_settings
    from bridge.parsers.markdown_parser import detect_kb_layer, parse_markdown
    from bridge.parsers.multi_format_parser import (
        UnsupportedFormat,
        parse_file,
        supported_extensions,
    )

    s = get_settings()
    p = Path(req.path)
    if not p.is_absolute():
        p = (s.hogwarts_kb_path / p).resolve()
    else:
        p = p.resolve()

    # Path-traversal guard: refuse anything outside HOGWARTS_KB_PATH.
    # Mirrors the same guard in MCP kb_read tool.
    try:
        p.relative_to(s.hogwarts_kb_path.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Path escapes KB root: {req.path}",
        )

    if not p.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {p}",
        )

    ext = p.suffix.lower()
    try:
        if ext == ".md":
            ir = parse_markdown(p)
        elif ext in supported_extensions():
            ir = parse_file(p)
        else:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported extension: {ext}",
            )
    except (FileNotFoundError, ValueError, UnsupportedFormat) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    rel = str(p.resolve().relative_to(s.hogwarts_kb_path.resolve()))
    layer = detect_kb_layer(p, s.hogwarts_kb_path)
    return IngestResponse(
        relative_path=rel,
        kind=ir["kind"],
        kb_layer=layer,
        content_hash=ir["content_hash"],
        raw_size=ir["raw_size"],
    )


@router.post(
    "/summarize",
    response_model=SummarizeResponse,
    summary="Local extractive summarization (no LLM)",
)
async def summarize(req: SummarizeRequest) -> SummarizeResponse:
    from bridge_utils import summarize_extractive

    res = summarize_extractive(
        req.text,
        target_chars=req.target_chars,
        max_sentences=req.max_sentences,
    )
    return SummarizeResponse(
        text=res.text,
        sentence_count=res.sentence_count,
        char_count=res.char_count,
        confidence=res.confidence,
        needs_llm_fallback=res.needs_llm_fallback,
        method=res.method,
    )


@router.post(
    "/classify",
    response_model=ClassifyResponse,
    summary="Suggest KB path + tags for a body of markdown",
)
async def classify(req: ClassifyRequest) -> ClassifyResponse:
    from bridge_utils import classify_path

    sug = classify_path(req.body, title_hint=req.title_hint)
    return ClassifyResponse(
        page_type=sug.page_type,
        suggested_path=sug.suggested_path,
        confidence=sug.confidence,
        tags=sug.tags,
        reasoning=sug.reasoning,
    )


@router.post(
    "/write/summary",
    response_model=WriteResponse,
    summary="Write a summary into wiki/summaries/ (auto-commit + optional push)",
    responses={
        403: {"description": "Path safety violation (writing outside allowed paths)"},
        409: {"description": "Git lock timeout (obsidian-git in progress)"},
    },
)
async def write_summary(req: WriteSummaryRequest) -> WriteResponse:
    from bridge.writers.kb_writer import (
        GitLockTimeout,
        KBWriteError,
        write_summary_to_kb,
    )

    try:
        res = write_summary_to_kb(
            title=req.title,
            body=req.body,
            sources=req.sources,
            related=req.related,
            tags=req.tags,
            slug=req.slug,
        )
    except GitLockTimeout as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except KBWriteError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    return WriteResponse(**res)


@router.post(
    "/write/analysis",
    response_model=WriteResponse,
    summary="Write an analysis into wiki/analyses/ (auto-commit + optional push)",
)
async def write_analysis(req: WriteSummaryRequest) -> WriteResponse:
    from bridge.writers.kb_writer import (
        GitLockTimeout,
        KBWriteError,
        write_analysis_to_kb,
    )

    try:
        res = write_analysis_to_kb(
            title=req.title,
            body=req.body,
            sources=req.sources,
            related=req.related,
            tags=req.tags,
            slug=req.slug,
        )
    except GitLockTimeout as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except KBWriteError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    return WriteResponse(**res)


@router.post(
    "/sync",
    summary="Run one-shot full sync of HOGWARTS_KB_PATH (BLOCKING in v0.53)",
    description=(
        "Synchronously scans all KB files. Blocks the response until done — "
        "use only on small KBs (<1000 files). v0.54 will dispatch to Celery. "
        "The sync runs in a worker thread so other requests stay responsive."
    ),
)
async def sync_endpoint() -> dict[str, Any]:
    import asyncio

    from bridge.watchers.kb_watcher import run_full_sync

    # Wrap the synchronous full-sync in a worker thread so we don't block
    # the FastAPI event loop. Other endpoints stay responsive.
    rc = await asyncio.to_thread(run_full_sync)
    return {"status": "ok" if rc == 0 else "error", "return_code": rc}


@router.get(
    "/mappings",
    summary="List KB path ↔ doc_id mappings (paginated)",
    description="Returns up to `limit` BridgeMapping rows. v0.53 stub: returns empty list "
    "until BridgeIngestStage persists rows (v0.54).",
)
async def list_mappings(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    # v0.53 stub — wiring to DB happens in v0.54 once bridge_ingest stage is wired.
    return {
        "items": [],
        "limit": limit,
        "offset": offset,
        "total": 0,
        "_note": "v0.53 stub: bridge_ingest persistence lands in v0.54",
    }
