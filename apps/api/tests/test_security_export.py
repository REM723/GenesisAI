"""AC-08: no provider key material reaches an export. Requires Postgres + Redis."""

SECRET = "sk-provider-SECRET-0987654321"


async def _auth(client) -> dict[str, str]:
    await client.post("/auth/register", json={"email": "sec@b.com", "password": "password123"})
    r = await client.post("/auth/login", json={"email": "sec@b.com", "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_export_never_contains_key_material(client) -> None:
    headers = await _auth(client)
    pid = (
        await client.post("/projects", json={"name": "S", "idea": "an idea"}, headers=headers)
    ).json()["id"]

    await client.post("/keys", json={"provider": "openai", "key": SECRET}, headers=headers)
    await client.post("/tests/generate", json={"project_id": pid}, headers=headers)

    res = await client.get(f"/exports/{pid}", headers=headers)
    assert res.status_code == 200
    archive = res.content
    assert SECRET.encode() not in archive
    assert b"sk-provider" not in archive
    assert b"encrypted_key" not in archive
