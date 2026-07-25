"""Full auth lifecycle: register → login → access → refresh rotation → logout/revocation.

Integration test — requires Postgres + Redis (skipped otherwise via conftest fixtures).
"""

CRED = {"email": "a@b.com", "password": "password123"}


async def test_full_auth_lifecycle(client) -> None:
    # register — response must not echo password or hash
    r = await client.post("/auth/register", json=CRED)
    assert r.status_code == 201
    assert "password" not in r.text and "hash" not in r.text

    # duplicate email rejected
    assert (await client.post("/auth/register", json=CRED)).status_code == 409

    # login issues a token pair
    r = await client.post("/auth/login", json=CRED)
    assert r.status_code == 200
    access, refresh = r.json()["access_token"], r.json()["refresh_token"]

    # wrong password
    bad = await client.post("/auth/login", json={**CRED, "password": "wrong-one-99"})
    assert bad.status_code == 401

    # protected route: token works, missing token is 401
    assert (
        await client.get("/keys", headers={"Authorization": f"Bearer {access}"})
    ).status_code == 200
    assert (await client.get("/keys")).status_code == 401

    # refresh rotates the token and invalidates the old one
    r = await client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    rotated = r.json()["refresh_token"]
    assert rotated != refresh
    assert (await client.post("/auth/refresh", json={"refresh_token": refresh})).status_code == 401

    # logout revokes the current refresh token
    new_access = r.json()["access_token"]
    out = await client.post(
        "/auth/logout",
        json={"refresh_token": rotated},
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert out.status_code == 204
    assert (await client.post("/auth/refresh", json={"refresh_token": rotated})).status_code == 401
