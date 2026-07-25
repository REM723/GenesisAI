"""The single read/write interface agents use for project context (SRS §2, AC-02).

No agent talks to Postgres or Chroma directly — everything goes through ContextMemory.
Writes fan out to the relational store (authoritative) and the vector store (recall);
reads do semantic search then hydrate full records, preserving similarity order.
"""

import uuid
from typing import Protocol

from .types import ContextKind, ContextRecord
from .vector import VectorStore


class RelationalStore(Protocol):
    async def add(self, record: ContextRecord) -> None: ...
    async def get_many(self, ids: list[str]) -> list[ContextRecord]: ...


class ContextMemory:
    def __init__(self, relational: RelationalStore, vector: VectorStore) -> None:
        self._relational = relational
        self._vector = vector

    async def write(
        self,
        project_id: str,
        kind: ContextKind,
        content: str,
        meta: dict[str, str] | None = None,
    ) -> ContextRecord:
        record = ContextRecord(
            id=str(uuid.uuid4()),
            project_id=project_id,
            kind=kind,
            content=content,
            meta=meta,
        )
        await self._relational.add(record)
        await self._vector.add(record.id, content, {"project_id": project_id, "kind": kind})
        return record

    async def read(
        self, project_id: str, query: str, k: int = 5, kind: ContextKind | None = None
    ) -> list[ContextRecord]:
        ids = await self._vector.query(project_id, query, k, kind)
        if not ids:
            return []
        records = await self._relational.get_many(ids)
        rank = {rec_id: i for i, rec_id in enumerate(ids)}
        return sorted(records, key=lambda r: rank.get(r.id, len(ids)))
