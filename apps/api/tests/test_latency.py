"""SRS §8: API read endpoints under 300ms p95 (excluding LLM). In-process measurement against
live Postgres + Redis. This covers the read-latency budget; the 1,000-concurrent target (AC-07)
needs a deployed stack and is exercised by scripts/loadtest.py."""

import time


async def test_read_endpoint_p95_within_budget(client) -> None:
    await client.post("/auth/register", json={"email": "lat@b.com", "password": "password123"})
    login = await client.post("/auth/login", json={"email": "lat@b.com", "password": "password123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    await client.get("/projects", headers=headers)  # warm

    timings: list[float] = []
    for _ in range(60):
        start = time.perf_counter()
        res = await client.get("/projects", headers=headers)
        timings.append((time.perf_counter() - start) * 1000)
        assert res.status_code == 200

    timings.sort()
    p95 = timings[int(len(timings) * 0.95) - 1]
    assert p95 < 300, f"read p95 {p95:.1f}ms exceeds the 300ms budget"
