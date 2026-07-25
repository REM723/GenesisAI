"""Rate limiting (SRS §7 / §9): the Redis counter blocks past the limit, and the HTTP layer
returns 429 with Retry-After. Requires Redis (+ Postgres for the HTTP path)."""

from app.ratelimit import _hit


async def test_counter_blocks_past_limit(redis_client) -> None:
    key = "rl:test:60"
    ok1, _ = await _hit(redis_client, key, 2, 60)
    ok2, _ = await _hit(redis_client, key, 2, 60)
    ok3, retry_after = await _hit(redis_client, key, 2, 60)
    assert ok1 and ok2 and not ok3
    assert retry_after >= 1


async def test_http_returns_429_with_retry_after(client, monkeypatch) -> None:
    monkeypatch.setattr("app.ratelimit.DEFAULT_LIMIT", 3)
    await client.post("/auth/register", json={"email": "rl@b.com", "password": "password123"})
    login = await client.post("/auth/login", json={"email": "rl@b.com", "password": "password123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    responses = [await client.get("/projects", headers=headers) for _ in range(6)]
    limited = [r for r in responses if r.status_code == 429]
    assert limited, "expected at least one 429"
    assert "Retry-After" in limited[0].headers
