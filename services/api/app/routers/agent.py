"""Agent output router: API-key-authenticated search and QA for external agents."""

import asyncio
import logging
import time
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import cast, func, select, Date
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_errors import AppException, ErrorCode
from shared_models import ApiKey, ApiUsageLog, ArchitectureNode, Asset, AssetChunk, KnowledgeDoc, KnowledgeDocVersion, SourceRef
from shared_schemas.agent import (
    AgentAskRequest,
    AgentAskResponse,
    AgentSearchHit,
    AgentSearchRequest,
    AgentSearchResponse,
    AgentUsageResponse,
    DailyUsage,
    EndpointUsage,
    SourceAsset,
    UsageGroupBy,
)
from shared_schemas.common import DataResponse, ErrorDetail

from app.deps import get_api_key_project, get_db, get_settings_dep
from app.services.search_service import SearchService
from app.services.qa_service import QAService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/agent", tags=["agent"])

_background_tasks: set[asyncio.Task] = set()


def _fire_and_forget(coro) -> None:
    """Schedule a coroutine as a background task with GC-safe reference."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


_RESP_AUTH = {
    401: {"description": "Unauthorized — invalid or revoked API key", "model": ErrorDetail},
    429: {"description": "Rate limited", "model": ErrorDetail},
}


async def _check_rate_limit(
    auth: tuple[ApiKey, uuid.UUID, uuid.UUID] = Depends(get_api_key_project),
    settings: Settings = Depends(get_settings_dep),
) -> tuple[ApiKey, uuid.UUID, uuid.UUID]:
    """Per-API-key rate limiting using Redis fixed-window counter."""
    api_key, project_id, kb_id = auth
    limit = api_key.rate_limit_per_minute
    if limit == 0:
        return auth  # no limit

    try:
        import redis
        r = redis.from_url(settings.redis_url, decode_responses=True)
        minute = int(time.time()) // 60
        key = f"rl:api:{api_key.id}:{minute}"
        count = r.incr(key)
        if count == 1:
            r.expire(key, 120)
        r.close()

        if count > limit:
            seconds_left = 60 - (int(time.time()) % 60)
            _fire_and_forget(_log_usage(api_key.id, "rate_limited", "ANY", 429, 0))
            raise AppException(
                ErrorCode.SYSTEM_RATE_LIMITED,
                status_code=429,
                detail={"retry_after": seconds_left},
            )
    except AppException:
        raise
    except Exception as e:
        logger.warning("Rate limit check failed (allowing request): %s", e)

    return auth


async def _log_usage(
    api_key_id: uuid.UUID,
    endpoint: str,
    method: str,
    status_code: int,
    latency_ms: int,
) -> None:
    """Write a usage log row in an independent session (BackgroundTask)."""
    from shared_models.database import async_session_factory

    async with async_session_factory() as session:
        try:
            log = ApiUsageLog(
                api_key_id=api_key_id,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                latency_ms=latency_ms,
                requested_at=datetime.now(timezone.utc),
            )
            session.add(log)
            await session.commit()
        except Exception as e:
            logger.warning("Failed to write usage log: %s", e)


async def _batch_load_arch_nodes(
    db: AsyncSession, node_ids: set[uuid.UUID]
) -> dict[uuid.UUID, ArchitectureNode]:
    """Batch-load architecture nodes and their ancestors iteratively."""
    arch_nodes_by_id: dict[uuid.UUID, ArchitectureNode] = {}
    ids_to_load = set(node_ids)
    while ids_to_load:
        result = await db.execute(
            select(ArchitectureNode).where(ArchitectureNode.id.in_(ids_to_load))
        )
        loaded = result.scalars().all()
        ids_to_load = set()
        for n in loaded:
            arch_nodes_by_id[n.id] = n
            if n.parent_id and n.parent_id not in arch_nodes_by_id:
                ids_to_load.add(n.parent_id)
    return arch_nodes_by_id


def _build_node_path_from_cache(
    node_id: uuid.UUID | None,
    arch_nodes_by_id: dict[uuid.UUID, ArchitectureNode],
) -> list[str]:
    """Build full path from root to node using pre-loaded cache."""
    if node_id is None or node_id not in arch_nodes_by_id:
        return []
    path: list[str] = []
    cur = node_id
    for _ in range(20):  # guard against cycles
        if cur not in arch_nodes_by_id:
            break
        path.append(arch_nodes_by_id[cur].node_name)
        cur = arch_nodes_by_id[cur].parent_id
        if cur is None:
            break
    path.reverse()
    return path


async def _batch_load_source_assets(
    db: AsyncSession, doc_version_pairs: list[tuple[uuid.UUID, int]]
) -> dict[uuid.UUID, list[SourceAsset]]:
    """Batch-load source assets for multiple docs in a single joined query."""
    if not doc_version_pairs:
        return {}

    doc_ids = [pair[0] for pair in doc_version_pairs]

    # Batch-load all relevant doc_version IDs
    dv_q = select(KnowledgeDocVersion.id, KnowledgeDocVersion.doc_id).where(
        KnowledgeDocVersion.doc_id.in_(doc_ids)
    )
    dv_rows = (await db.execute(dv_q)).all()

    # Build a set of valid (doc_id -> version -> dv_id) and filter to matching versions
    version_map = {pair[0]: pair[1] for pair in doc_version_pairs}
    dv_id_to_doc: dict[uuid.UUID, uuid.UUID] = {}
    dv_ids: list[uuid.UUID] = []
    for row in dv_rows:
        dv_id_to_doc[row.id] = row.doc_id
        dv_ids.append(row.id)

    if not dv_ids:
        return {}

    # Single joined query for all source assets
    q = (
        select(Asset.id, Asset.filename, Asset.asset_type, SourceRef.doc_version_id)
        .select_from(SourceRef)
        .join(AssetChunk, AssetChunk.id == SourceRef.asset_chunk_id)
        .join(Asset, Asset.id == AssetChunk.asset_id)
        .where(SourceRef.doc_version_id.in_(dv_ids))
        .distinct()
    )
    rows = (await db.execute(q)).all()

    result: dict[uuid.UUID, list[SourceAsset]] = {}
    for row in rows:
        doc_id = dv_id_to_doc.get(row.doc_version_id)
        if doc_id is None:
            continue
        result.setdefault(doc_id, []).append(
            SourceAsset(asset_id=row.id, filename=row.filename, asset_type=row.asset_type)
        )
    return result


@router.post(
    "/search",
    response_model=DataResponse[AgentSearchResponse],
    summary="Agent search — API-key authenticated",
    description="Hybrid search over the project's knowledge base. Enriches results with node_path and source_assets.",
    responses={200: {"description": "Search results returned"}, **_RESP_AUTH},
)
async def agent_search(
    body: AgentSearchRequest,
    auth: tuple[ApiKey, uuid.UUID, uuid.UUID] = Depends(_check_rate_limit),
    db: AsyncSession = Depends(get_db),
):
    t0 = time.monotonic()
    api_key, project_id, kb_id = auth

    svc = SearchService(db, kb_id)
    results, total = await svc.hybrid_search(
        project_id=project_id,
        query=body.query,
        page=1,
        page_size=body.top_k,
    )

    # Batch-load all KnowledgeDocs by doc_id set
    doc_ids = {r["doc_id"] for r in results}
    if doc_ids:
        doc_q = select(KnowledgeDoc).where(KnowledgeDoc.id.in_(doc_ids))
        doc_result = await db.execute(doc_q)
        docs_by_id = {d.id: d for d in doc_result.scalars().all()}
    else:
        docs_by_id = {}

    # Batch-load architecture nodes iteratively (load all node_ids, then parents)
    node_ids = {d.node_id for d in docs_by_id.values() if d.node_id is not None}
    arch_nodes_by_id = await _batch_load_arch_nodes(db, node_ids) if node_ids else {}

    # Batch-load source assets with a single joined query
    doc_version_pairs = [
        (d.id, d.current_version)
        for d in docs_by_id.values()
    ]
    assets_by_doc = await _batch_load_source_assets(db, doc_version_pairs)

    # Build enriched hits
    hits: list[AgentSearchHit] = []
    for r in results:
        doc_id = r["doc_id"]
        doc = docs_by_id.get(doc_id)

        # Fix #9: skip deleted docs instead of using fallback
        if doc is None:
            continue

        node_path = _build_node_path_from_cache(doc.node_id, arch_nodes_by_id)
        source_assets = assets_by_doc.get(doc_id, [])

        hits.append(
            AgentSearchHit(
                doc_id=doc_id,
                title=r.get("title", ""),
                doc_type=r.get("doc_type", ""),
                snippet=r.get("snippet", ""),
                score=r.get("score"),
                node_path=node_path,
                source_assets=source_assets,
            )
        )

    latency = int((time.monotonic() - t0) * 1000)
    _fire_and_forget(_log_usage(api_key.id, "/v1/agent/search", "POST", 200, latency))

    return DataResponse(data=AgentSearchResponse(results=hits, total=total))


@router.post(
    "/ask",
    response_model=DataResponse[AgentAskResponse],
    summary="Agent QA — API-key authenticated",
    description="Non-streaming RAG question answering over the project's knowledge base.",
    responses={
        200: {"description": "Answer generated"},
        **_RESP_AUTH,
        400: {"description": "Model not configured", "model": ErrorDetail},
    },
)
async def agent_ask(
    body: AgentAskRequest,
    auth: tuple[ApiKey, uuid.UUID, uuid.UUID] = Depends(_check_rate_limit),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    t0 = time.monotonic()
    api_key, project_id, kb_id = auth

    svc = QAService(db, kb_id, settings)
    result = await svc.ask(project_id, body.question, body.top_k)

    latency = int((time.monotonic() - t0) * 1000)
    _fire_and_forget(_log_usage(api_key.id, "/v1/agent/ask", "POST", 200, latency))

    return DataResponse(
        data=AgentAskResponse(
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            related_questions=result.get("related_questions", []),
        )
    )


@router.get(
    "/usage",
    response_model=DataResponse[AgentUsageResponse],
    summary="API key usage statistics",
    description="Query usage summary for the authenticated API key.",
    responses={200: {"description": "Usage statistics returned"}, **_RESP_AUTH},
)
async def agent_usage(
    auth: tuple[ApiKey, uuid.UUID, uuid.UUID] = Depends(get_api_key_project),
    db: AsyncSession = Depends(get_db),
    start_date: date | None = Query(None, description="Start date (YYYY-MM-DD), default 7 days ago"),
    end_date: date | None = Query(None, description="End date (YYYY-MM-DD), default today"),
    group_by: UsageGroupBy = Query(UsageGroupBy.day, description="Group by day or endpoint"),
):
    api_key, project_id, kb_id = auth

    today = date.today()
    start = start_date or (today - timedelta(days=6))
    end = end_date or today

    # Totals
    totals_q = select(
        func.count().label("total_requests"),
        func.count().filter(ApiUsageLog.status_code >= 400).label("total_errors"),
    ).where(
        ApiUsageLog.api_key_id == api_key.id,
        cast(ApiUsageLog.requested_at, Date) >= start,
        cast(ApiUsageLog.requested_at, Date) <= end,
    )
    totals_row = (await db.execute(totals_q)).one()

    daily: list[DailyUsage] | None = None
    by_endpoint: list[EndpointUsage] | None = None

    if group_by == UsageGroupBy.day:
        day_q = (
            select(
                cast(ApiUsageLog.requested_at, Date).label("d"),
                func.count().label("requests"),
                func.count().filter(ApiUsageLog.status_code >= 400).label("errors"),
                func.coalesce(func.avg(ApiUsageLog.latency_ms), 0).label("avg_lat"),
            )
            .where(
                ApiUsageLog.api_key_id == api_key.id,
                cast(ApiUsageLog.requested_at, Date) >= start,
                cast(ApiUsageLog.requested_at, Date) <= end,
            )
            .group_by("d")
            .order_by("d")
        )
        rows = (await db.execute(day_q)).all()
        daily = [
            DailyUsage(date=r.d, requests=r.requests, errors=r.errors, avg_latency_ms=int(r.avg_lat))
            for r in rows
        ]
    else:
        ep_q = (
            select(
                ApiUsageLog.endpoint,
                func.count().label("requests"),
                func.count().filter(ApiUsageLog.status_code >= 400).label("errors"),
                func.coalesce(func.avg(ApiUsageLog.latency_ms), 0).label("avg_lat"),
            )
            .where(
                ApiUsageLog.api_key_id == api_key.id,
                cast(ApiUsageLog.requested_at, Date) >= start,
                cast(ApiUsageLog.requested_at, Date) <= end,
            )
            .group_by(ApiUsageLog.endpoint)
            .order_by(func.count().desc())
        )
        rows = (await db.execute(ep_q)).all()
        by_endpoint = [
            EndpointUsage(endpoint=r.endpoint, requests=r.requests, errors=r.errors, avg_latency_ms=int(r.avg_lat))
            for r in rows
        ]

    return DataResponse(
        data=AgentUsageResponse(
            api_key_id=api_key.id,
            period={"start": start.isoformat(), "end": end.isoformat()},
            total_requests=totals_row.total_requests,
            total_errors=totals_row.total_errors,
            daily=daily,
            by_endpoint=by_endpoint,
        )
    )
