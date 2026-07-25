"""SQL-backed RelationalStore for context memory — the concrete half genesis_memory needs.

apps/api owns the DB, so the store lives here and is injected into ContextMemory. This keeps
the dependency direction clean (api -> genesis_memory), never the reverse.
"""

import uuid

from genesis_memory import ContextRecord
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import ContextItemRepository


class SqlContextStore:
    """Implements genesis_memory.RelationalStore over the context_items table."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = ContextItemRepository(session)

    async def add(self, record: ContextRecord) -> None:
        await self._repo.add(
            id=uuid.UUID(record.id),
            project_id=uuid.UUID(record.project_id),
            kind=record.kind,
            content=record.content,
            meta=record.meta,
        )

    async def get_many(self, ids: list[str]) -> list[ContextRecord]:
        rows = await self._repo.get_many([uuid.UUID(i) for i in ids])
        return [
            ContextRecord(
                id=str(r.id),
                project_id=str(r.project_id),
                kind=r.kind,  # DB CHECK guarantees a valid ContextKind
                content=r.content,
                meta=r.meta,
                created_at=r.created_at,
            )
            for r in rows
        ]
