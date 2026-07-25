"""Orchestrator integration (Phase 5): a full run records steps + status, a timed-out agent
leaves partial artifacts and marks the run `timeout`, and progress is published over SSE.
Requires Postgres + Redis. Runner is faked — no live model calls."""

import asyncio
import json

from app.db import make_sessionmaker
from app.models import Project, Run, User
from app.orchestrator import Orchestrator, run_channel
from app.repositories import AgentRunRepository, RunRepository


class FakeRunner:
    def __init__(self, behavior: dict[str, object] | None = None) -> None:
        self._behavior = behavior or {}

    async def run(self, agent: str, prompt: str) -> str:
        b = self._behavior.get(agent)
        if callable(b):
            return await b(agent, prompt)  # type: ignore[no-any-return]
        return f"{agent}-output"


async def _make_run(maker) -> tuple:
    async with maker() as session:
        user = User(email="orch@b.com", password_hash="x")
        session.add(user)
        await session.flush()
        project = Project(user_id=user.id, name="P", idea="A habit tracker.")
        session.add(project)
        await session.flush()
        run = Run(project_id=project.id, status="queued")
        session.add(run)
        await session.flush()
        await session.commit()
        return run.id, project.id


async def test_full_run_records_steps_and_status(engine, redis_client) -> None:  # AC-03
    maker = make_sessionmaker(engine)
    run_id, project_id = await _make_run(maker)

    status = await Orchestrator(maker, redis_client, FakeRunner()).run(
        run_id, project_id, "A habit tracker."
    )
    assert status == "succeeded"

    async with maker() as session:
        assert (await RunRepository(session).get(run_id)).status == "succeeded"
        steps = await AgentRunRepository(session).list_for_run(run_id)
        agents = [s.agent for s in steps]
        for expected in ("product_manager", "architect", "backend", "qa", "documentation"):
            assert expected in agents
        assert all(s.status == "succeeded" for s in steps)


async def test_timeout_marks_run_and_keeps_partial(engine, redis_client) -> None:
    maker = make_sessionmaker(engine)
    run_id, project_id = await _make_run(maker)

    async def slow(agent: str, prompt: str) -> str:
        await asyncio.sleep(0.5)
        return "late"

    status = await Orchestrator(
        maker, redis_client, FakeRunner({"backend": slow}), timeouts={"backend": 0.01}
    ).run(run_id, project_id, "idea")
    assert status == "timeout"

    async with maker() as session:
        assert (await RunRepository(session).get(run_id)).status == "timeout"
        steps = await AgentRunRepository(session).list_for_run(run_id)
        agents = {s.agent for s in steps}
        assert {"product_manager", "architect"} <= agents  # partial artifacts retained
        assert any(s.agent == "backend" and s.status == "timeout" for s in steps)


async def test_progress_is_published_over_sse(engine, redis_client) -> None:
    maker = make_sessionmaker(engine)
    run_id, project_id = await _make_run(maker)

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(run_channel(run_id))
    task = asyncio.create_task(
        Orchestrator(maker, redis_client, FakeRunner()).run(run_id, project_id, "idea")
    )

    seen: list[dict] = []
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
        if message is None:
            continue
        event = json.loads(message["data"])
        seen.append(event)
        if str(event["type"]).startswith("run_"):
            break
    await task
    await pubsub.unsubscribe(run_channel(run_id))
    await pubsub.aclose()

    types = {e["type"] for e in seen}
    assert "start" in types
    assert "complete" in types
    assert any(t.startswith("run_") for t in types)
