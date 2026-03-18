"""Tests for job CRUD endpoints."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_job(client: AsyncClient, auth_headers: dict):
    # First create a project
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Job Test Project"},
        headers=auth_headers,
    )
    project_id = proj_resp.json()["data"]["id"]

    resp = await client.post(
        "/v1/jobs",
        json={"project_id": project_id, "job_type": "ingest"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["job_type"] == "ingest"
    assert data["status"] == "pending"
    assert data["retry_count"] == 0


@pytest.mark.asyncio
async def test_list_jobs(client: AsyncClient, auth_headers: dict):
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Job List Project"},
        headers=auth_headers,
    )
    project_id = proj_resp.json()["data"]["id"]

    await client.post(
        "/v1/jobs",
        json={"project_id": project_id, "job_type": "ingest"},
        headers=auth_headers,
    )
    await client.post(
        "/v1/jobs",
        json={"project_id": project_id, "job_type": "classify"},
        headers=auth_headers,
    )

    resp = await client.get(
        f"/v1/jobs?project_id={project_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) >= 2
    assert body["meta"]["total"] >= 2


@pytest.mark.asyncio
async def test_get_job(client: AsyncClient, auth_headers: dict):
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Job Get Project"},
        headers=auth_headers,
    )
    project_id = proj_resp.json()["data"]["id"]

    create_resp = await client.post(
        "/v1/jobs",
        json={"project_id": project_id, "job_type": "ingest"},
        headers=auth_headers,
    )
    job_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/v1/jobs/{job_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["job_type"] == "ingest"


@pytest.mark.asyncio
async def test_retry_failed_job(client: AsyncClient, auth_headers: dict, db_session):
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Job Retry Project"},
        headers=auth_headers,
    )
    project_id = proj_resp.json()["data"]["id"]

    create_resp = await client.post(
        "/v1/jobs",
        json={"project_id": project_id, "job_type": "ingest"},
        headers=auth_headers,
    )
    job_id = create_resp.json()["data"]["id"]

    # Manually set job to failed
    from shared_models import Job
    from sqlalchemy import select

    result = await db_session.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
    job = result.scalar_one()
    job.status = "failed"
    job.error_message = "some error"
    await db_session.flush()

    resp = await client.post(f"/v1/jobs/{job_id}/retry", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "pending"
    assert data["retry_count"] == 1


@pytest.mark.asyncio
async def test_retry_non_failed_job(client: AsyncClient, auth_headers: dict):
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Job Retry Fail Project"},
        headers=auth_headers,
    )
    project_id = proj_resp.json()["data"]["id"]

    create_resp = await client.post(
        "/v1/jobs",
        json={"project_id": project_id, "job_type": "ingest"},
        headers=auth_headers,
    )
    job_id = create_resp.json()["data"]["id"]

    resp = await client.post(f"/v1/jobs/{job_id}/retry", headers=auth_headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/v1/jobs/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404
