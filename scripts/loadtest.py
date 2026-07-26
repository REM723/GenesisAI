"""Concurrency load harness for the §8 budgets / AC-07 (1,000 concurrent users).

No new dependency: asyncio + httpx (already in the dev set). Point it at a deployed API URL;
the in-sandbox read-latency budget is covered by apps/api/tests/test_latency.py.

Usage:
    python scripts/loadtest.py --url http://localhost:8000/health \\
        --concurrency 1000 --requests 20000 [--bearer <jwt>]
"""

import argparse
import asyncio
import time

import httpx


async def _worker(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    queue: asyncio.Queue[int],
    latencies: list[float],
    errors: list[int],
) -> None:
    while True:
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            return
        start = time.perf_counter()
        try:
            res = await client.get(url, headers=headers)
            latencies.append((time.perf_counter() - start) * 1000)
            if res.status_code >= 500:
                errors.append(res.status_code)
        except httpx.HTTPError:
            errors.append(0)
        finally:
            queue.task_done()


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    return sorted(values)[min(len(values) - 1, int(len(values) * p))]


async def run(url: str, concurrency: int, requests: int, bearer: str | None) -> None:
    headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
    queue: asyncio.Queue[int] = asyncio.Queue()
    for i in range(requests):
        queue.put_nowait(i)

    latencies: list[float] = []
    errors: list[int] = []
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)

    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=30, limits=limits) as client:
        workers = [
            asyncio.create_task(_worker(client, url, headers, queue, latencies, errors))
            for _ in range(concurrency)
        ]
        await asyncio.gather(*workers)
    elapsed = time.perf_counter() - start

    ok = len(latencies)
    print(f"url            {url}")
    print(f"concurrency    {concurrency}")
    print(f"requests       {requests} ({ok} ok, {len(errors)} errors)")
    print(f"throughput     {ok / elapsed:,.0f} req/s over {elapsed:.1f}s")
    print(f"latency p50    {_pct(latencies, 0.50):.1f} ms")
    print(f"latency p95    {_pct(latencies, 0.95):.1f} ms")
    print(f"latency p99    {_pct(latencies, 0.99):.1f} ms")


def main() -> None:
    parser = argparse.ArgumentParser(description="GenesisAI load harness")
    parser.add_argument("--url", required=True)
    parser.add_argument("--concurrency", type=int, default=100)
    parser.add_argument("--requests", type=int, default=5000)
    parser.add_argument("--bearer", default=None)
    args = parser.parse_args()
    asyncio.run(run(args.url, args.concurrency, args.requests, args.bearer))


if __name__ == "__main__":
    main()
