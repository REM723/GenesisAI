"""AC-08 / NFR-03: a stored provider key never appears in any response or log line.

Integration test — requires Postgres + Redis.
"""

import logging

SECRET = "sk-supersecret-KEYVALUE-0987654321"


async def test_api_key_never_leaks(client, caplog) -> None:
    await client.post("/auth/register", json={"email": "k@b.com", "password": "password123"})
    login = await client.post("/auth/login", json={"email": "k@b.com", "password": "password123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    with caplog.at_level(logging.DEBUG):
        created = await client.post(
            "/keys", json={"provider": "openai", "key": SECRET}, headers=headers
        )
        assert created.status_code == 201
        assert SECRET not in created.text
        body = created.json()
        assert "key" not in body and "encrypted_key" not in body

        listed = await client.get("/keys", headers=headers)
        assert listed.status_code == 200
        assert SECRET not in listed.text
        assert "encrypted_key" not in listed.text

    # the plaintext key must not have reached any log record
    assert SECRET not in caplog.text
