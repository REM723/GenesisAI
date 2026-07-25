# packages/memory — genesis_memory

Per-project context memory (SRS §2, AC-02). One interface, `ContextMemory`, that agents use
to persist and recall requirements, decisions, and artifacts. Writes fan out to a relational
store (authoritative) and a Chroma vector store (semantic recall); reads do a vector search
then hydrate full records. **No agent touches Postgres or Chroma directly.**

## Public interface

```python
from genesis_memory import ContextMemory, ChromaVectorStore

memory = ContextMemory(relational_store, ChromaVectorStore(chroma_client))
await memory.write(project_id, "decision", "Use PostgreSQL for persistence.")
hits = await memory.read(project_id, "which database?", k=5)  # -> [ContextRecord, ...]
```

- `RelationalStore` is a protocol; `apps/api` supplies `SqlContextStore` over the
  `context_items` table (migration 0002).
- `ChromaVectorStore` takes any chromadb client (HttpClient in prod, EphemeralClient in
  tests) and an optional embedding function (defaults to Chroma's built-in local model).

## Test

```bash
pip install -e packages/memory -r requirements-dev.txt
pytest packages/memory/tests    # real Chroma EphemeralClient + deterministic offline embedder
```
