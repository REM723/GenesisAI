"""Phase 5 exit criteria for the graph itself (offline, fake runner, no live calls):
AC-03 full run, resume-without-repeat, per-agent timeout, and the reviewer gate."""

import asyncio
from collections.abc import Callable

import pytest
from genesis_agents import build_workflow, initial_state
from langgraph.checkpoint.memory import MemorySaver


class Recorder:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def __call__(self, event: dict) -> None:
        self.events.append(event)

    def completed(self) -> list[str]:
        return [e["agent"] for e in self.events if e["type"] == "complete"]


class FakeRunner:
    """Returns canned output, or applies per-agent behavior (coroutine fn or Exception)."""

    def __init__(self, behavior: dict[str, object] | None = None) -> None:
        self.calls: list[str] = []
        self._behavior = behavior or {}

    async def run(self, agent: str, prompt: str) -> str:
        self.calls.append(agent)
        b = self._behavior.get(agent)
        if isinstance(b, Callable):  # type: ignore[arg-type]
            return await b(agent, prompt)  # type: ignore[operator,no-any-return]
        if isinstance(b, Exception):
            raise b
        return f"{agent}-output"


def _cfg(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _state() -> dict:
    return dict(initial_state("run-1", "prj-1", "A habit tracker with streaks."))


async def test_full_run_completes_in_order() -> None:  # AC-03
    rec = Recorder()
    graph = build_workflow(FakeRunner(), on_event=rec)
    final = await graph.ainvoke(_state(), config=_cfg("run-ac03"))

    order = rec.completed()
    for agent in ("product_manager", "architect", "backend", "qa", "documentation"):
        assert agent in order
    idx = order.index
    assert (
        idx("product_manager")
        < idx("architect")
        < idx("backend")
        < idx("qa")
        < idx("documentation")
    )
    assert set(final["outputs"]) >= {
        "product_manager",
        "architect",
        "backend",
        "qa",
        "documentation",
    }


async def test_resume_skips_completed_steps() -> None:
    saver = MemorySaver()
    state = {"n": 0}

    async def backend_flaky(agent: str, prompt: str) -> str:
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("transient failure")
        return "backend-output"

    runner = FakeRunner({"backend": backend_flaky})
    graph = build_workflow(runner, checkpointer=saver)
    cfg = _cfg("run-resume")

    with pytest.raises(RuntimeError):
        await graph.ainvoke(_state(), config=cfg)
    assert runner.calls.count("product_manager") == 1
    assert runner.calls.count("architect") == 1

    await graph.ainvoke(None, config=cfg)  # resume from checkpoint
    assert runner.calls.count("product_manager") == 1  # not repeated
    assert runner.calls.count("architect") == 1
    assert runner.calls.count("backend") == 2  # failed once, then succeeded


async def test_agent_timeout_raises_and_keeps_partial_artifacts() -> None:
    rec = Recorder()

    async def slow(agent: str, prompt: str) -> str:
        await asyncio.sleep(0.5)
        return "late"

    graph = build_workflow(FakeRunner({"backend": slow}), on_event=rec, timeouts={"backend": 0.01})
    with pytest.raises(TimeoutError):
        await graph.ainvoke(_state(), config=_cfg("run-timeout"))

    completed = rec.completed()
    assert "product_manager" in completed and "architect" in completed  # partial artifacts kept
    assert "backend" not in completed
    assert any(e["type"] == "timeout" and e["agent"] == "backend" for e in rec.events)


async def test_reviewer_returns_work_once() -> None:
    counter = {"n": 0}

    class FailOnce:
        async def review(self, agent: str, artifact: str) -> bool:
            counter["n"] += 1
            return counter["n"] != 1  # fail the first review, pass afterwards

    runner = FakeRunner()
    graph = build_workflow(runner, reviewer=FailOnce())
    await graph.ainvoke(_state(), config=_cfg("run-review"))
    assert runner.calls.count("backend") == 2  # regenerated exactly once
