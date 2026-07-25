"""Agent run SSE stream (SRS §6 / §9): GET /agents/runs/{run_id}/stream.

Subscribes to the run's Redis channel and relays orchestrator events as Server-Sent Events.
The full POST /agents/run trigger + 202 conventions land in Phase 6.
"""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_redis, get_session
from app.models import User
from app.orchestrator import Orchestrator, run_channel
from app.ratelimit import rate_limit
from app.repositories import ProjectRepository, RunRepository
from app.schemas import AgentRunIn, RunAccepted

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post(
    "/run",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RunAccepted,
    dependencies=[Depends(rate_limit)],
)
async def start_run(
    body: AgentRunIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> RunAccepted:
    project = await ProjectRepository(session).get_owned(body.project_id, user.id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    runs = RunRepository(session)
    if body.run_id is not None:  # resume
        run = await runs.get(body.run_id)
        if run is None or run.project_id != project.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    else:
        run = await runs.create(project_id=project.id)
    run_id, project_id, idea = run.id, project.id, project.idea
    await session.commit()  # persist the run before the background task reads it

    orchestrator = Orchestrator(
        request.app.state.sessionmaker, request.app.state.redis, request.app.state.agent_runner
    )
    task = asyncio.create_task(orchestrator.run(run_id, project_id, idea))
    request.app.state.background_tasks.add(task)
    task.add_done_callback(request.app.state.background_tasks.discard)
    return RunAccepted(run_id=run_id, status="queued")


@router.get("/runs/{run_id}/stream")
async def stream_run(
    run_id: uuid.UUID,
    redis: Redis = Depends(get_redis),
    _user: User = Depends(get_current_user),
) -> StreamingResponse:
    channel = run_channel(run_id)

    async def events() -> AsyncIterator[str]:
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = message["data"]
                yield f"data: {data}\n\n"
                try:
                    if str(json.loads(data).get("type", "")).startswith("run_"):
                        break  # terminal event ends the stream
                except (json.JSONDecodeError, TypeError):
                    continue
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()  # type: ignore[no-untyped-call]

    return StreamingResponse(events(), media_type="text/event-stream")
