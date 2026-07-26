"""Audit log surface (SRS §7) + RBAC. Admin reads logs, members are refused. Requires PG+Redis."""

from app.db import make_sessionmaker
from app.repositories import UserRepository


async def _login(client, email: str) -> dict[str, str]:
    await client.post("/auth/register", json={"email": email, "password": "password123"})
    r = await client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_member_cannot_read_logs(client) -> None:
    headers = await _login(client, "member@b.com")
    assert (await client.get("/logs", headers=headers)).status_code == 403


async def test_admin_reads_audit_trail(client, engine) -> None:
    await _login(client, "admin@b.com")  # registration writes an auth.register log
    maker = make_sessionmaker(engine)
    async with maker() as session:
        user = await UserRepository(session).get_by_email("admin@b.com")
        assert user is not None
        user.role = "admin"
        await session.commit()

    login = await client.post(
        "/auth/login", json={"email": "admin@b.com", "password": "password123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    res = await client.get("/logs", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert "next_cursor" in body
    assert "auth.register" in [i["event"] for i in body["items"]]
