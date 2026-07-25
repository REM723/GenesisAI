"""Repository layer — the only place that runs queries (no raw SQL in route handlers).

Only the aggregates auth/keys need in Phase 1 are implemented (users, api_keys).
Other tables get repositories when their phase uses them.
"""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApiKey, ContextItem, Log, Prompt, PromptVersion, User


async def write_log(
    session: AsyncSession,
    *,
    event: str,
    user_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append an audit/system event (§7). Never pass secrets in `payload`."""
    session.add(Log(event=event, user_id=user_id, payload=payload))


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
