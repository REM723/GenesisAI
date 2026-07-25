"""Runs the optimizer loop and persists the full history (Phase 4, FR-06/FR-07).

The pure optimization lives in genesis_agents (DB-free, offline). This thin service is the
only place the loop's output touches the DB: it stores the final prompt in `prompts` and
every iteration in `prompt_versions`, in order.
"""

import uuid

from genesis_agents import LoopEngine
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Prompt
from app.repositories import PromptRepository, PromptVersionRepository


async def optimize_and_persist(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    type: str,
    idea: str,
    engine: LoopEngine | None = None,
) -> Prompt:
    iterations = (engine or LoopEngine()).run(idea)
    final = iterations[-1]

    prompt = await PromptRepository(session).create(
        project_id=project_id, type=type, content=final.prompt, score=final.score
    )
    versions = PromptVersionRepository(session)
    for it in iterations:
        await versions.add(
            prompt_id=prompt.id, version=it.version, content=it.prompt, score=it.score
        )
    return prompt
