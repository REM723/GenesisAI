"""Contract tests for the SRS §9 endpoints: shapes, status codes, auth, 422, pagination,
202 + run_id, and the OpenAPI surface. Integration — requires Postgres + Redis."""

import uuid


async def _auth(client) -> dict[str, str]:
    await client.post("/auth/register", json={"email": "api@b.com", "password": "password123"})
    login = await client.post("/auth/login", json={"email": "api@b.com", "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _project(client, headers) -> str:
    r = await client.post(
        "/projects", json={"name": "P", "idea": "A habit tracker with streaks."}, headers=headers
    )
    return r.json()["id"]


async def test_create_get_list_projects(client) -> None:
    headers = await _auth(client)

    created = await client.post(
        "/projects", json={"name": "P1", "idea": "A habit tracker."}, headers=headers
    )
    assert created.status_code == 201
    assert set(created.json()) >= {"id", "name", "status", "created_at"}
    pid = created.json()["id"]

    assert (await client.post("/projects", json={"name": ""}, headers=headers)).status_code == 422
    assert (await client.post("/projects", json={"name": "x", "idea": "y"})).status_code == 401

    detail = await client.get(f"/projects/{pid}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["idea"] == "A habit tracker."
    assert detail.json()["latest_run"] is None

    listed = await client.get("/projects?limit=1", headers=headers)
    assert listed.status_code == 200
    assert "items" in listed.json() and "next_cursor" in listed.json()

    assert (await client.get(f"/projects/{uuid.uuid4()}", headers=headers)).status_code == 404


async def test_prompts_generate(client) -> None:
    headers = await _auth(client)
    pid = await _project(client, headers)
    r = await client.post("/prompts/generate", json={"project_id": pid}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["score"] >= 0.8
    assert len(body["versions"]) >= 1


async def test_agents_run_returns_202_and_run_id(client) -> None:
    headers = await _auth(client)
    pid = await _project(client, headers)
    r = await client.post("/agents/run", json={"project_id": pid}, headers=headers)
    assert r.status_code == 202
    assert uuid.UUID(r.json()["run_id"])
    assert r.json()["status"] == "queued"


async def test_code_review_and_tests_generate(client) -> None:
    headers = await _auth(client)
    pid = await _project(client, headers)

    review = await client.post("/code/review", json={"project_id": pid}, headers=headers)
    assert review.status_code == 200
    assert review.json()["passed"] is True
    assert review.json()["files_reviewed"] == 0

    tests = await client.post("/tests/generate", json={"project_id": pid}, headers=headers)
    assert tests.status_code == 200
    assert "qa-output" in tests.json()["content"]


async def test_export_not_ready(client) -> None:
    headers = await _auth(client)
    assert (await client.get(f"/exports/{uuid.uuid4()}", headers=headers)).status_code == 404
    assert (await client.get(f"/exports/{uuid.uuid4()}")).status_code == 401


async def test_openapi_covers_section9(client) -> None:
    paths = (await client.get("/openapi.json")).json()["paths"]
    for path in (
        "/projects",
        "/projects/{project_id}",
        "/prompts/generate",
        "/agents/run",
        "/code/review",
        "/tests/generate",
        "/exports/{project_id}",
        "/agents/runs/{run_id}/stream",
    ):
        assert path in paths, path
