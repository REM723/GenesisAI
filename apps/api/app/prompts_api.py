"""Prompt generation endpoint (SRS §9): runs the Phase-4 optimizer loop and persists."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session
from app.models import User
from app.prompt_service import optimize_and_persist
from app.ratelimit import rate_limit
from app.repositories import ProjectRepository, PromptVersionRepository
from app.schemas import PromptGenerateIn, PromptOut, PromptVersionOut

router = APIRouter(prefix="/prompts", tags=["prompts"], dependencies=[Depends(rate_limit)])


@router.post("/generate", response_model=PromptOut)
async def generate_prompts(
    body: PromptGenerateIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> PromptOut:
    project = await ProjectRepository(session).get_owned(body.project_id, user.id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    prompt = await optimize_and_persist(
        session, project_id=project.id, type="build", idea=project.idea
    )
    versions = await PromptVersionRepository(session).list_for_prompt(prompt.id)
    return PromptOut(
        id=prompt.id,
        type=prompt.type,
        content=prompt.content,
        score=prompt.score,
        versions=[PromptVersionOut(version=v.version, score=v.score) for v in versions],
    )
