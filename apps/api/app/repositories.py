"""Repository layer — the only place that runs queries (no raw SQL in route handlers).

Only the aggregates auth/keys need in Phase 1 are implemented (users, api_keys).
Other tables get repositories when their phase uses them.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AgentRun,
    ApiKey,
    ContextItem,
    Document,
    GeneratedCode,
    Log,
    Project,
    Prompt,
    PromptVersion,
    Run,
    User,
)


async def write_log(
    session: AsyncSession,
    *,
    event: str,
    user_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append an audit/system event (§7). Never pass secrets in `payload`."""
    session.add(Log(event=event, user_id=user_id, payload=payload))


class LogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self, *, limit: int, cursor: tuple[datetime, uuid.UUID] | None = None
    ) -> Sequence[Log]:
        query = select(Log)
        if cursor is not None:
            ts, cid = cursor
            query = query.where(or_(Log.created_at < ts, and_(Log.created_at == ts, Log.id < cid)))
        query = query.order_by(Log.created_at.desc(), Log.id.desc()).limit(limit)
        return (await self._session.scalars(query)).all()


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, email: str, password_hash: str, role: str = "member") -> User:
        user = User(email=email, password_hash=password_hash, role=role)
        self._session.add(user)
        await self._session.flush()
        return user

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.scalars(select(User).where(User.email == email))
        return result.first()


class ApiKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: uuid.UUID, provider: str, encrypted_key: str) -> ApiKey:
        key = ApiKey(user_id=user_id, provider=provider, encrypted_key=encrypted_key)
        self._session.add(key)
        await self._session.flush()
        return key

    async def list_for_user(self, user_id: uuid.UUID) -> Sequence[ApiKey]:
        result = await self._session.scalars(
            select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at)
        )
        return result.all()

    async def get_for_user(self, user_id: uuid.UUID, provider: str) -> ApiKey | None:
        result = await self._session.scalars(
            select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.provider == provider)
        )
        return result.first()


class ContextItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        id: uuid.UUID,
        project_id: uuid.UUID,
        kind: str,
        content: str,
        meta: dict[str, Any] | None,
    ) -> ContextItem:
        item = ContextItem(id=id, project_id=project_id, kind=kind, content=content, meta=meta)
        self._session.add(item)
        await self._session.flush()
        return item

    async def get_many(self, ids: list[uuid.UUID]) -> Sequence[ContextItem]:
        if not ids:
            return []
        result = await self._session.scalars(select(ContextItem).where(ContextItem.id.in_(ids)))
        return result.all()


class PromptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, project_id: uuid.UUID, type: str, content: str, score: float | None
    ) -> Prompt:
        prompt = Prompt(project_id=project_id, type=type, content=content, score=score)
        self._session.add(prompt)
        await self._session.flush()
        return prompt


class PromptVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self, *, prompt_id: uuid.UUID, version: int, content: str, score: float | None
    ) -> PromptVersion:
        row = PromptVersion(prompt_id=prompt_id, version=version, content=content, score=score)
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_for_prompt(self, prompt_id: uuid.UUID) -> Sequence[PromptVersion]:
        result = await self._session.scalars(
            select(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
            .order_by(PromptVersion.version)
        )
        return result.all()


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: uuid.UUID, name: str, idea: str) -> Project:
        project = Project(user_id=user_id, name=name, idea=idea, status="draft")
        self._session.add(project)
        await self._session.flush()
        return project

    async def get_owned(self, project_id: uuid.UUID, user_id: uuid.UUID) -> Project | None:
        project = await self._session.get(Project, project_id)
        if project is None or project.user_id != user_id:
            return None
        return project

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        cursor: tuple[datetime, uuid.UUID] | None = None,
    ) -> Sequence[Project]:
        # keyset pagination on (created_at, id) descending.
        query = select(Project).where(Project.user_id == user_id)
        if cursor is not None:
            ts, cid = cursor
            query = query.where(
                or_(
                    Project.created_at < ts,
                    and_(Project.created_at == ts, Project.id < cid),
                )
            )
        query = query.order_by(Project.created_at.desc(), Project.id.desc()).limit(limit)
        return (await self._session.scalars(query)).all()


class GeneratedCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, project_id: uuid.UUID, path: str, language: str, content: str, version: int = 1
    ) -> GeneratedCode:
        row = GeneratedCode(
            project_id=project_id, path=path, language=language, content=content, version=version
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_for_project(self, project_id: uuid.UUID) -> Sequence[GeneratedCode]:
        result = await self._session.scalars(
            select(GeneratedCode).where(GeneratedCode.project_id == project_id)
        )
        return result.all()


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_project(self, project_id: uuid.UUID) -> Sequence[Document]:
        result = await self._session.scalars(
            select(Document).where(Document.project_id == project_id)
        )
        return result.all()


class RunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, project_id: uuid.UUID) -> Run:
        run = Run(project_id=project_id, status="queued")
        self._session.add(run)
        await self._session.flush()
        return run

    async def get(self, run_id: uuid.UUID) -> Run | None:
        return await self._session.get(Run, run_id)

    async def latest_for_project(self, project_id: uuid.UUID) -> Run | None:
        result = await self._session.scalars(
            select(Run).where(Run.project_id == project_id).order_by(Run.created_at.desc()).limit(1)
        )
        return result.first()

    async def update_status(
        self,
        run_id: uuid.UUID,
        *,
        status: str,
        current_agent: str | None = None,
        error: str | None = None,
    ) -> None:
        run = await self._session.get(Run, run_id)
        if run is None:
            return
        run.status = status
        if current_agent is not None:
            run.current_agent = current_agent
        if error is not None:
            run.error = error


class AgentRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        run_id: uuid.UUID,
        project_id: uuid.UUID,
        agent: str,
        status: str,
        output: dict[str, Any] | None = None,
        tokens: int = 0,
        duration_ms: int | None = None,
    ) -> AgentRun:
        row = AgentRun(
            run_id=run_id,
            project_id=project_id,
            agent=agent,
            status=status,
            output=output,
            tokens=tokens,
            duration_ms=duration_ms,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_for_run(self, run_id: uuid.UUID) -> Sequence[AgentRun]:
        result = await self._session.scalars(
            select(AgentRun).where(AgentRun.run_id == run_id).order_by(AgentRun.created_at)
        )
        return result.all()
