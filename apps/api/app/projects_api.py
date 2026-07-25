"""Project endpoints (SRS §9). GET /projects (list) is a documented divergence for FR-02."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session
from app.models import User
from app.pagination import decode_cursor, encode_cursor
from app.ratelimit import rate_limit
from app.repositories import (
    DocumentRepository,
    GeneratedCodeRepository,
    ProjectRepository,
    RunRepository,
)
from app.schemas import (
    ArtifactRef,
    ProjectCreate,
    ProjectDetail,
    ProjectOut,
    ProjectPage,
    RunSummary,
)

router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[Depends(rate_limit)])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProjectOut)
async def create_project(
    body: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> object:
    return await ProjectRepository(session).create(user_id=user.id, name=body.name, idea=body.idea)


@router.get("", response_model=ProjectPage)
async def list_projects(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ProjectPage:
    decoded = None
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid cursor") from exc

    rows = await ProjectRepository(session).list_for_user(user.id, limit=limit + 1, cursor=decoded)
    items = rows[:limit]
    next_cursor = encode_cursor(items[-1].created_at, items[-1].id) if len(rows) > limit else None
    return ProjectPage(items=[ProjectOut.model_validate(p) for p in items], next_cursor=next_cursor)


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ProjectDetail:
    project = await ProjectRepository(session).get_owned(project_id, user.id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    code = await GeneratedCodeRepository(session).list_for_project(project_id)
    docs = await DocumentRepository(session).list_for_project(project_id)
    latest = await RunRepository(session).latest_for_project(project_id)
    return ProjectDetail(
        id=project.id,
        name=project.name,
        idea=project.idea,
        status=project.status,
        created_at=project.created_at,
        code=[ArtifactRef.model_validate(c) for c in code],
        documents=[ArtifactRef.model_validate(d) for d in docs],
        latest_run=RunSummary.model_validate(latest) if latest else None,
    )
