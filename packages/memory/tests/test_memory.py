"""AC-02: a later agent recalls an earlier agent's decision via the memory interface,
without that decision being re-supplied in its query.

Uses a real Chroma EphemeralClient (in-process) with a deterministic offline embedder —
no model download, no server, no live calls.
"""

import hashlib
import math
import re

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from genesis_memory import ChromaVectorStore, ContextMemory, ContextRecord

PROJECT = "prj-1"
_DIM = 256


def _embed(text: str) -> list[float]:
    vec = [0.0] * _DIM
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        vec[int(hashlib.md5(tok.encode()).hexdigest(), 16) % _DIM] += 1.0  # noqa: S324
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class DeterministicEmbedding(EmbeddingFunction[Documents]):
    """Bag-of-words hashing embedder — deterministic, offline, good enough to rank overlap."""

    def __init__(self) -> None:
        pass

    def __call__(self, input: Documents) -> Embeddings:  # noqa: A002 - chroma's arg name
        return [_embed(t) for t in input]  # type: ignore[return-value]

    @staticmethod
    def name() -> str:
        return "deterministic-test"

    def get_config(self) -> dict:
        return {}

    @staticmethod
    def build_from_config(config: dict) -> "DeterministicEmbedding":
        return DeterministicEmbedding()


class FakeRelational:
    """In-memory authoritative store implementing the RelationalStore protocol."""

    def __init__(self) -> None:
        self._items: dict[str, ContextRecord] = {}

    async def add(self, record: ContextRecord) -> None:
        self._items[record.id] = record

    async def get_many(self, ids: list[str]) -> list[ContextRecord]:
        return [self._items[i] for i in ids if i in self._items]


def _memory() -> ContextMemory:
    client = chromadb.EphemeralClient()
    vector = ChromaVectorStore(client, embedding_function=DeterministicEmbedding())
    return ContextMemory(FakeRelational(), vector)


async def test_later_agent_recalls_earlier_decision() -> None:
    memory = _memory()
    # "Architect agent" records decisions.
    await memory.write(
        PROJECT,
        "decision",
        "Use PostgreSQL via SQLAlchemy for backend persistence and data storage.",
    )
    await memory.write(
        PROJECT, "decision", "Use Next.js App Router with Tailwind for the frontend UI."
    )

    # "Backend agent" later asks about storage — never given the decision text.
    results = await memory.read(PROJECT, "what storage did the backend decide to use?", k=1)

    assert results, "expected a recalled decision"
    assert "PostgreSQL" in results[0].content


async def test_kind_filter_scopes_recall() -> None:
    memory = _memory()
    await memory.write(PROJECT, "requirement", "The app must send weekly email summaries.")
    await memory.write(PROJECT, "decision", "Emails are sent via a scheduled worker.")

    only_reqs = await memory.read(PROJECT, "weekly email summaries", k=5, kind="requirement")
    assert only_reqs
    assert all(r.kind == "requirement" for r in only_reqs)


async def test_read_with_no_writes_returns_empty() -> None:
    memory = _memory()
    assert await memory.read(PROJECT, "anything", k=3) == []


async def test_recall_is_scoped_per_project() -> None:
    memory = _memory()
    await memory.write("prj-A", "decision", "Project A uses GraphQL for its API layer.")
    results = await memory.read("prj-B", "which API style", k=5)
    assert results == []  # project B has no context; A's decision must not leak
