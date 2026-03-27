"""Agent output router: API-key-authenticated search and QA for external agents."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_models import ApiKey, ArchitectureNode, Asset, AssetChunk, KnowledgeDoc, KnowledgeDocVersion, SourceRef
from shared_schemas.agent import (
    AgentAskRequest,
    AgentAskResponse,
    AgentSearchHit,
    AgentSearchRequest,
    AgentSearchResponse,
    SourceAsset,
)
from shared_schemas.common import DataResponse, ErrorDetail

from app.deps import get_api_key_project, get_db, get_settings_dep
from app.services.search_service import SearchService
from app.services.qa_service import QAService

router = APIRouter(prefix="/v1/agent", tags=["agent"])

_RESP_AUTH = {
    401: {"description": "Unauthorized — invalid or revoked API key", "model": ErrorDetail},
}


async def _build_node_path(db: AsyncSession, node_id: uuid.UUID | None) -> list[str]:
    """Walk up the architecture_node tree to build the full path from root to node."""
    if node_id is None:
        return []

    path: list[str] = []
    current_id = node_id

    # Guard against cycles — max 20 levels
    for _ in range(20):
        result = await db.execute(
            select(ArchitectureNode).where(ArchitectureNode.id == current_id)
        )
        node = result.scalar_one_or_none()
        if node is None:
            break
        path.append(node.node_name)
        if node.parent_id is None:
            break
        current_id = node.parent_id

    path.reverse()
    return path


async def _get_source_assets(
    db: AsyncSession, doc_id: uuid.UUID, current_version: int
) -> list[SourceAsset]:
    """Get source assets for a document via source_ref -> asset_chunk -> asset."""
    # Find the doc_version record for the current version
    dv_result = await db.execute(
        select(KnowledgeDocVersion.id).where(
            KnowledgeDocVersion.doc_id == doc_id,
            KnowledgeDocVersion.version == current_version,
        )
    )
    dv_id = dv_result.scalar_one_or_none()
    if dv_id is None:
        return []

    # Join source_ref -> asset_chunk -> asset
    q = (
        select(Asset.id, Asset.filename, Asset.asset_type)
        .select_from(SourceRef)
        .join(AssetChunk, AssetChunk.id == SourceRef.asset_chunk_id)
        .join(Asset, Asset.id == AssetChunk.asset_id)
        .where(SourceRef.doc_version_id == dv_id)
        .distinct()
    )
    rows = (await db.execute(q)).all()

    return [
        SourceAsset(asset_id=row.id, filename=row.filename, asset_type=row.asset_type)
        for row in rows
    ]


@router.post(
    "/search",
    response_model=DataResponse[AgentSearchResponse],
    summary="Agent search — API-key authenticated",
    description="Hybrid search over the project's knowledge base. Enriches results with node_path and source_assets.",
    responses={200: {"description": "Search results returned"}, **_RESP_AUTH},
)
async def agent_search(
    body: AgentSearchRequest,
    auth: tuple[ApiKey, uuid.UUID, uuid.UUID] = Depends(get_api_key_project),
    db: AsyncSession = Depends(get_db),
):
    api_key, project_id, tenant_id = auth

    svc = SearchService(db, tenant_id)
    results, total = await svc.hybrid_search(
        project_id=project_id,
        query=body.query,
        page=1,
        page_size=body.top_k,
    )

    # Enrich each result with node_path and source_assets
    hits: list[AgentSearchHit] = []
    for r in results:
        doc_id = r["doc_id"]

        # Get the doc record for node_id and current_version
        doc_result = await db.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
        )
        doc = doc_result.scalar_one_or_none()

        node_path = await _build_node_path(db, doc.node_id if doc else None)
        source_assets = await _get_source_assets(
            db, doc_id, doc.current_version if doc else 1
        )

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
    auth: tuple[ApiKey, uuid.UUID, uuid.UUID] = Depends(get_api_key_project),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    api_key, project_id, tenant_id = auth

    svc = QAService(db, tenant_id, settings)
    result = await svc.ask(project_id, body.question, body.top_k)

    return DataResponse(
        data=AgentAskResponse(
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            related_questions=result.get("related_questions", []),
        )
    )
