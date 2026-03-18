"""Tests for text search endpoint."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shared_models import KnowledgeDoc, KnowledgeDocVersion


@pytest_asyncio.fixture(loop_scope="session")
async def search_fixture(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    """Create project with docs for search testing."""
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Search Test Project"},
        headers=auth_headers,
    )
    project_id = uuid.UUID(proj_resp.json()["data"]["id"])

    from sqlalchemy import select
    from shared_models import User
    users_result = await db_session.execute(select(User).limit(1))
    user = users_result.scalar_one()

    # Doc 1: title matches "退款"
    doc1 = KnowledgeDoc(
        id=uuid.uuid4(),
        project_id=project_id,
        doc_type="topic",
        title="客服退款规则文档",
        current_version=1,
        status="published",
    )
    db_session.add(doc1)
    await db_session.flush()

    ver1 = KnowledgeDocVersion(
        id=uuid.uuid4(),
        doc_id=doc1.id,
        version=1,
        content_md="# 退款规则\n\n7天无理由退货，3-5个工作日到账",
        change_reason="初始版本",
        created_by=user.id,
    )
    db_session.add(ver1)

    # Doc 2: content matches "物流"
    doc2 = KnowledgeDoc(
        id=uuid.uuid4(),
        project_id=project_id,
        doc_type="topic",
        title="订单处理流程",
        current_version=1,
        status="draft",
    )
    db_session.add(doc2)
    await db_session.flush()

    ver2 = KnowledgeDocVersion(
        id=uuid.uuid4(),
        doc_id=doc2.id,
        version=1,
        content_md="# 订单处理\n\n下单后物流配送通常需要2-3天",
        change_reason="初始版本",
        created_by=user.id,
    )
    db_session.add(ver2)

    # Doc 3: no match for common queries
    doc3 = KnowledgeDoc(
        id=uuid.uuid4(),
        project_id=project_id,
        doc_type="glossary",
        title="术语表",
        current_version=1,
        status="draft",
    )
    db_session.add(doc3)
    await db_session.flush()

    ver3 = KnowledgeDocVersion(
        id=uuid.uuid4(),
        doc_id=doc3.id,
        version=1,
        content_md="# 术语\n\nSKU: 库存量单位",
        change_reason="初始版本",
        created_by=user.id,
    )
    db_session.add(ver3)

    await db_session.flush()

    return {"project_id": project_id, "doc1_id": doc1.id, "doc2_id": doc2.id}


@pytest.mark.asyncio
async def test_search_by_title(client: AsyncClient, auth_headers: dict, search_fixture: dict):
    """Should find docs matching title."""
    resp = await client.post(
        "/v1/search/text",
        json={"project_id": str(search_fixture["project_id"]), "query": "退款"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["total"] >= 1
    titles = [hit["title"] for hit in data["data"]]
    assert any("退款" in t for t in titles)


@pytest.mark.asyncio
async def test_search_by_content(client: AsyncClient, auth_headers: dict, search_fixture: dict):
    """Should find docs matching content_md."""
    resp = await client.post(
        "/v1/search/text",
        json={"project_id": str(search_fixture["project_id"]), "query": "物流"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["total"] >= 1
    # The matched doc should be "订单处理流程"
    titles = [hit["title"] for hit in data["data"]]
    assert "订单处理流程" in titles


@pytest.mark.asyncio
async def test_search_no_results(client: AsyncClient, auth_headers: dict, search_fixture: dict):
    """Should return empty when no match."""
    resp = await client.post(
        "/v1/search/text",
        json={"project_id": str(search_fixture["project_id"]), "query": "不存在的关键词xyz"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["total"] == 0
    assert data["data"] == []


@pytest.mark.asyncio
async def test_search_empty_query_rejected(client: AsyncClient, auth_headers: dict, search_fixture: dict):
    """Empty query should be rejected with 422."""
    resp = await client.post(
        "/v1/search/text",
        json={"project_id": str(search_fixture["project_id"]), "query": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_snippet_contains_context(client: AsyncClient, auth_headers: dict, search_fixture: dict):
    """Snippet should contain matched text."""
    resp = await client.post(
        "/v1/search/text",
        json={"project_id": str(search_fixture["project_id"]), "query": "退款"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    hits = resp.json()["data"]
    assert len(hits) >= 1
    # At least one hit should have snippet containing "退款"
    snippets = [h["snippet"] for h in hits]
    assert any("退款" in s for s in snippets)
