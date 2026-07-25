"""Agent run SSE stream (SRS §6 / §9): GET /agents/runs/{run_id}/stream.

Subscribes to the run's Redis channel and relays orchestrator events as Server-Sent Events.
The full POST /agents/run trigger + 202 conventions land in Phase 6.
"""

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from app.deps import get_current_user, get_redis
from app.models import User
from app.orchestrator import run_channel

router = APIRouter(prefix="/agents", tags=["agents"])


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
