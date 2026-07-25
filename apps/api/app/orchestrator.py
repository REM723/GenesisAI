"""Runs the agent graph for a run and owns every side effect (Phase 5).

The graph (genesis_agents) is DB-free; this orchestrator supplies the `on_event` callback
that persists each step to `agent_runs`, writes artifacts to context memory, publishes SSE
progress to Redis, and updates the run's status. On timeout the run is marked `timeout` and
the artifacts already written are retained.

ponytail: MemorySaver checkpointing gives in-process resume; a persistent LangGraph saver is
the upgrade for cross-process resume. The runs/agent_runs tables are the durable status of record.
"""

import json
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from genesis_agents import AgentRunner, Reviewer, build_workflow, initial_state
from genesis_memory import ContextMemory
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories import AgentRunRepository, RunRepository


def run_channel(run_id: uuid.UUID | str) -> str:
    return f"run:{run_id}"


class Orchestrator:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        redis: Redis,
        runner: AgentRunner,
        *,
        reviewer: Reviewer | None = None,
        memory: ContextMemory | None = None,
        timeouts: dict[str, float] | None = None,
    ) -> None:
        self._sessions = session_maker
        self._redis = redis
        self._runner = runner
        self._reviewer = reviewer
        self._memory = memory
        self._timeouts = timeouts

    async def _publish(self, run_id: str, event: dict[str, Any]) -> None:
        await self._redis.publish(run_channel(run_id), json.dumps(event))

    def _on_event(self, project_id: uuid.UUID) -> Callable[[dict[str, Any]], Awaitable[None]]:
        async def handle(event: dict[str, Any]) -> None:
            run_id = uuid.UUID(event["run_id"])
            async with self._sessions() as session:
                runs = RunRepository(session)
                if event["type"] == "start":
                    await runs.update_status(run_id, status="running", current_agent=event["agent"])
                elif event["type"] == "complete":
                    await AgentRunRepository(session).add(
                        run_id=run_id,
                        project_id=project_id,
                        agent=event["agent"],
                        status="succeeded",
                        output={"text": event["output"]},
                    )
                    if self._memory is not None:
                        await self._memory.write(
                            str(project_id), event["produces"], event["output"]
                        )
                elif event["type"] == "timeout":
                    await AgentRunRepository(session).add(
                        run_id=run_id,
                        project_id=project_id,
                        agent=event["agent"],
                        status="timeout",
                    )
                await session.commit()
            await self._publish(event["run_id"], event)

        return handle

    async def run(self, run_id: uuid.UUID, project_id: uuid.UUID, idea: str) -> str:
        graph = build_workflow(
            self._runner,
            reviewer=self._reviewer,
            on_event=self._on_event(project_id),
            timeouts=self._timeouts,
        )
        config = {"configurable": {"thread_id": str(run_id)}}
        status = "succeeded"
        error: str | None = None
        try:
            await graph.ainvoke(initial_state(str(run_id), str(project_id), idea), config=config)
        except TimeoutError:
            status = "timeout"
        except Exception as exc:  # noqa: BLE001 - record any agent failure, then surface via status
            status, error = "failed", str(exc)

        async with self._sessions() as session:
            await RunRepository(session).update_status(run_id, status=status, error=error)
            await session.commit()
        await self._publish(
            str(run_id), {"type": f"run_{status}", "run_id": str(run_id), "status": status}
        )
        return status
