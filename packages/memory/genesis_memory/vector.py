"""Vector store abstraction + a ChromaDB implementation.

The embedding function is injectable so tests run offline with a deterministic embedder
and no model download. Chroma calls are sync; we offload them to a thread.
"""

import asyncio
from typing import Any, Protocol


class VectorStore(Protocol):
    async def add(self, id: str, text: str, metadata: dict[str, str]) -> None: ...
    async def query(
        self, project_id: str, text: str, k: int, kind: str | None = None
    ) -> list[str]: ...


class ChromaVectorStore:
    """One Chroma collection keyed by project_id/kind metadata.

    `client` is a chromadb Client (HttpClient in prod, EphemeralClient in tests);
    `embedding_function` defaults to Chroma's built-in local model when None.
    """

    def __init__(
        self, client: Any, embedding_function: Any = None, collection: str = "context"
    ) -> None:
        self._collection = client.get_or_create_collection(
            name=collection, embedding_function=embedding_function
        )

    async def add(self, id: str, text: str, metadata: dict[str, str]) -> None:
        await asyncio.to_thread(
            self._collection.add, ids=[id], documents=[text], metadatas=[metadata]
        )

    async def query(self, project_id: str, text: str, k: int, kind: str | None = None) -> list[str]:
        where: dict[str, Any] = (
            {"project_id": project_id}
            if kind is None
            else {"$and": [{"project_id": project_id}, {"kind": kind}]}
        )
        result = await asyncio.to_thread(
            self._collection.query, query_texts=[text], n_results=k, where=where
        )
        ids = result.get("ids") or []
        return list(ids[0]) if ids else []
