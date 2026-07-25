"""Code review, test generation, and export download (SRS §9).

Thin for MVP: /code/review runs the reviewer over stored code; /tests/generate runs the QA
agent once over stored code; /exports/{id} is wired but packaging lands in Phase 8 (404 until).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from genesis_agents import AlwaysPassReviewer
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session
from app.models import User
from app.ratelimit import rate_limit
from app.repositories import GeneratedCodeRepository, ProjectRepository
from app.schemas import CodeReviewIn, CodeReviewOut, TestsGenerateIn, TestsGenerateOut

router = APIRouter(tags=["artifacts"], dependencies=[Depends(rate_limit)])


async def _owned_project(session: AsyncSession, project_id: uuid.UUID, user: User) -> object:
    project = await ProjectRepository(session).get_owned(project_id, user.id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


@router.post("/code/review", response_model=CodeReviewOut)
async def review_code(
    body: CodeReviewIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CodeReviewOut:
    await _owned_project(session, body.project_id, user)
    files = await GeneratedCodeRepository(session).list_for_project(body.project_id)
    reviewer = AlwaysPassReviewer()
    passed = all([await reviewer.review("backend", f.content) for f in files])
    return CodeReviewOut(project_id=body.project_id, passed=passed, files_reviewed=len(files))


@router.post("/tests/generate", response_model=TestsGenerateOut)
async def generate_tests(
    body: TestsGenerateIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> TestsGenerateOut:
    project = await _owned_project(session, body.project_id, user)
    files = await GeneratedCodeRepository(session).list_for_project(body.project_id)
    context = "\n\n".join(f.content for f in files) or project.idea  # type: ignore[attr-defined]
    prompt = f"Write unit and integration tests for the following code:\n\n{context}"
    content = await request.app.state.agent_runner.run("qa", prompt)
    await GeneratedCodeRepository(session).create(
        project_id=body.project_id,
        path="tests/test_generated.py",
        language="python",
        content=content,
    )
    return TestsGenerateOut(project_id=body.project_id, content=content)


@router.get("/exports/{export_id}")
async def download_export(
    export_id: uuid.UUID,
    _user: User = Depends(get_current_user),
) -> None:
    # Packaging is built in Phase 8; no export artifacts exist yet.
    raise HTTPException(
        status.HTTP_404_NOT_FOUND, "Export not available (packaging lands in Phase 8)"
    )
