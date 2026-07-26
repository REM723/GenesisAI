"""GET /exports/{project_id} contract (Phase 8). Requires Postgres + Redis."""

import uuid


async def _auth(client) -> dict[str, str]:
    await client.post("/auth/register", json={"email": "exp@b.com", "password": "password123"})
    login = await client.post("/auth/login", json={"email": "exp@b.com", "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _project(client, headers) -> str:
    r = await client.post("/projects", json={"name": "Exp", "idea": "an idea"}, headers=headers)
    return r.json()["id"]


async def test_export_streams_zip_after_artifacts_exist(client) -> None:
    headers = await _auth(client)
    pid = await _project(client, headers)
    # /tests/generate stores a generated_code artifact, giving the project something to export.
    await client.post("/tests/generate", json={"project_id": pid}, headers=headers)

    res = await client.get(f"/exports/{pid}", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert res.content[:2] == b"PK"  # zip magic bytes


async def test_export_empty_project_is_404(client) -> None:
    headers = await _auth(client)
    pid = await _project(client, headers)
    assert (await client.get(f"/exports/{pid}", headers=headers)).status_code == 404


async def test_export_requires_auth(client) -> None:
    assert (await client.get(f"/exports/{uuid.uuid4()}")).status_code == 401
