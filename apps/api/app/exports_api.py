"""Export download (SRS §9): GET /exports/{project_id} streams the packaged archive.

The id is the project id (documented divergence: §9 says {id}, we scope exports to a project).
No exports table needed; the archive is built on demand from stored artifacts (re-export safe).
"""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session
from app.export_service import assemble_files, build_archive
from app.models import User
from app.ratelimit import rate_limit
from app.repositories import (
    DocumentRepository,
    GeneratedCodeRepository,
    ProjectRepository,
    write_log,
)

router = APIRouter(tags=["exports"], dependencies=[Depends(rate_limit)])


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"


@router.get("/exports/{project_id}")
async def download_export(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    project = await ProjectRepository(session).get_owned(project_id, user.id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    code = await GeneratedCodeRepository(session).list_for_project(project_id)
    docs = await DocumentRepository(session).list_for_project(project_id)
    if not code and not docs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nothing to export yet")

    archive = build_archive(assemble_files(project.name, code, docs))
    await write_log(session, event="project.export", user_id=user.id)
    filename = f"{_slug(project.name)}.zip"
    return Response(
        content=archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
