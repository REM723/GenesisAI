# packages/memory

Per-project context store: relational records (requirements, decisions, artifacts) plus
vector recall over ChromaDB. Single read/write interface for agents — no agent touches the
DB or vector store directly.

**Status:** stub. Implemented in Phase 3.
**Public interface:** TBD (`read(query)` / `write(record)`).
**Tests:** `pytest packages/memory` (none yet).
