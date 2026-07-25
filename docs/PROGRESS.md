# GenesisAI — Build Progress Tracker

**Purpose:** single source of truth for what's done, what's next, and the decisions made.
Re-read this at the start of every session/phase. Update it at the end of every phase.
Authoritative specs remain `docs/PRD.md` and `docs/SRS.md`; this only tracks execution.

**Last updated:** 2026-07-26 (end of Phase 4)
**Current position:** Phase 4 complete and reviewed. Phase 5 not yet started.
**GitHub:** https://github.com/REM723/GenesisAI — one commit pushed per phase (no co-author trailer).

---

## Working rules (from the implementation brief)

- One phase at a time; complete fully, run exit criteria, stop for review. No rolling ahead.
- Ask before: adding a dep not in SRS; changing a migrated schema; altering a §9 API
  contract; adding a service/process boundary.
- Assume freely: file/module naming, helper structure, test layout, log wording.
- Standards: Python type hints + Pydantic + ruff + mypy strict, no bare except, DI via
  Depends. TS strict, Server Components default. Repository layer, forward-only reversible
  migrations. Conventional Commits. No secrets in repo/logs/responses/exports.

---

## Phase status

| Phase | Title | Status |
|---|---|---|
| 0 | Foundation (monorepo, tooling, docker, CI) | ✅ Done |
| 1 | Data layer + authentication | ✅ Done |
| 2 | LLM router | ✅ Done |
| 3 | Context memory | ✅ Done |
| 4 | Prompt optimizer + loop engine | ✅ Done |
| 5 | Agent workflow (LangGraph) | ⏳ Next |
| 6 | API surface | ⬜ Not started |
| 7 | Frontend | ⬜ Not started |
| 8 | Export + doc generation | ⬜ Not started |
| 9 | Hardening | ⬜ Not started |

---

## Phase 0 — Foundation ✅

Scaffolded §13 monorepo; ruff/mypy/ESLint/Prettier/pre-commit; `docker-compose` (Postgres,
Redis, ChromaDB, optional Ollama); `.env.example`; PR CI. `/health` endpoint + one test.

**Verified:** ruff/format/mypy/pytest green; web tsc/lint/build green; all 3 compose
services **healthy** (chroma healthcheck fixed to `/api/v1/heartbeat`). No `make` on
Windows — README documents raw-command equivalents. CI workflow written; not run remotely
(no git remote here).

## Phase 1 — Data layer + authentication ✅

All 10 §5 tables (`app/models.py`), initial migration (`migrations/versions/0001_init.py`),
repository layer (`app/repositories.py`), self-owned JWT auth (`app/auth.py`,
`app/security.py`, `app/deps.py`), AES-GCM key storage (`app/security.py`,
`app/api_keys.py`).

**Decisions:** SQLAlchemy 2.0 + Alembic; self-owned JWT (not Supabase Auth); refresh-token
state in Redis (no extra table); `users.role ∈ {admin, member}`, project owner = `user_id`;
`logs.user_id` SET NULL; UUID PKs. Full list in
`docs/architecture/0001-phase1-divergences.md`.

**Verified (live Postgres + Redis via docker):** migration upgrade→downgrade→upgrade clean;
10 tests pass (7 unit + 3 integration) — full auth lifecycle incl. refresh rotation +
revocation, and API-key-never-leaks; ruff/format/mypy strict clean.

**Deferred from Phase 1:** repositories only for `users`/`api_keys` (others per phase);
`require_role` implemented but not yet wired to endpoints; coverage tooling (`pytest-cov`)
not added — no coverage number yet; audit-log *read* surface is Phase 9.

**Open gap carried forward:** §9 references run-level `/agents/runs/{id}` and `/exports/{id}`
but §5 has no `runs`/`exports` table. Decision deferred to Phase 5/8.

---

## Phase 2 — LLM router ✅

`packages/router/genesis_router`: `types.py`, `errors.py`, `providers.py`, `router.py`.
Installable as `genesis_router` (nested package; `pip install -e packages/router`, wired
into CI + Makefile). All 7 providers behind one `OpenAICompatibleProvider` (LangChain
`ChatOpenAI` over each OpenAI-compatible endpoint); `REGISTRY` holds per-provider base_url,
pricing, and capability metadata (a tunable calibration table).

**Decisions:** LangChain (`langchain-openai`) client, one adapter not seven; `Router`
selects cheapest-satisfying provider and falls back cheapest-first on `ProviderError`
subclasses (rate-limit/timeout/unavailable); non-`ProviderError` propagates (it's a bug).
Router returns a `Usage` ledger; **DB persistence of tokens/cost deferred to Phase 5**
(needs the run record) — keeps `packages/router` DB-free.

**Verified:** ruff/format/mypy strict clean (18 files); 11 router tests pass (mocked
providers, no live calls) — cheapest selection, capability filtering, fallback on each
recoverable error, all-fail raises, non-provider error propagates, key-missing skip,
token/cost accounting across a run, add-provider-is-one-row, real registry has all 7.
Full suite: 21 passed.

**Deferred:** live provider smoke test (AC-05 "runs on ≥3 providers") is Phase 9; token→DB
persistence is Phase 5.

## Phase 3 — Context memory ✅

`packages/memory/genesis_memory`: `types.py` (ContextRecord/ContextKind), `vector.py`
(`VectorStore` protocol + `ChromaVectorStore`), `memory.py` (`ContextMemory` + `RelationalStore`
protocol). `apps/api`: `ContextItem` model + `ContextItemRepository` + migration `0002` +
`app/memory_store.py` (`SqlContextStore`). Installable as `genesis_memory` (CI/Makefile
updated).

**Decisions:** one generic `context_items` table (kind ∈ {requirement,decision,artifact});
Chroma built-in local embedding as the default, deterministic offline embedder injected in
tests (no download, no live calls); single collection keyed by `project_id`/`kind` metadata;
`ContextMemory` fans writes to relational (authoritative) + vector (recall), reads do vector
search then hydrate records in similarity order. Dependency direction: `apps/api` →
`genesis_memory` (SqlContextStore lives in api, implements the store protocol).

**Verified:** AC-02 proven — `test_later_agent_recalls_earlier_decision` (real Chroma
EphemeralClient) recalls an earlier "agent" decision from a query that never restates it;
plus kind-filter, empty-read, and per-project isolation tests; `SqlContextStore` round-trip
against live Postgres. Migrations 0001+0002 apply up/down/up on a fresh DB (head =
`0002_context_items`). ruff/format/mypy strict clean (22 files). Full suite: 26 passed.

**Notes:** chromadb resolved to 1.5.9 (>=0.5 allowed 1.x); test embedder subclasses
`chromadb.api.types.EmbeddingFunction`. mypy skips numpy stubs (3.12 syntax) via override.

**Post-Phase-2 addition (user request):** added **Groq** provider (`GROQ_API_KEY`,
`llama-3.3-70b-versatile`) as one `REGISTRY` row — an 8th provider, distinct from xAI's
`grok`. Divergence from SRS §4's 7-provider list, noted here; no new dependency (Groq is
OpenAI-compatible via the existing adapter).

## Phase 4 — Prompt optimizer + loop engine ✅

`packages/agents/genesis_agents`: `scoring.py` (heuristic 0–1 scorer), `optimizer.py`
(`PromptOptimizer.initial`/`improve`), `loop.py` (`LoopEngine.run` → ordered `Iteration`
list). `apps/api`: `PromptRepository` + `PromptVersionRepository` + `app/prompt_service.py`
(`optimize_and_persist` writes final prompt to `prompts`, each iteration to `prompt_versions`).
Installable as `genesis_agents` (CI/Makefile/testpaths wired).

**Decisions:** heuristic (rule-based) scoring + rule-based rewrite — deterministic, offline,
no keys; threshold 0.8, iteration cap 6 (both configurable). `improve()` adds the highest-
weight missing section each pass, so history is a genuine monotonic refinement.
`PromptOptimizer.improve` is the seam for a future LLM rewriter. Pure logic in
`packages/agents` (offline-testable); DB persistence isolated in `apps/api` (no schema change
— reuses §5 `prompts`/`prompt_versions`).

**Verified:** AC-01 — all 20 sample ideas reach ≥0.8 within the cap; version history
contiguous (1..n) and non-decreasing; iteration cap terminates a no-op optimizer; NFR-02 —
p95 optimize latency ≪ 5s (heuristic, sub-ms); persistence test writes ordered history to
`prompt_versions` against live Postgres. ruff/format/mypy strict clean (26 files). Full
suite: 32 passed.

## Phase 5 — Agent workflow (LangGraph) ⏳ (next)

**Goal (SRS §6):** LangGraph state machine — PM → Architect → Backend → Frontend → QA →
DevOps → Documentation, each with §6 inputs/outputs. Checkpoint after every step (resumable);
per-agent timeouts; Code Reviewer gate after code gen (returns work once); stream progress
over SSE at `GET /agents/runs/{run_id}/stream`. Uses the router (Phase 2), memory (Phase 3),
and optimizer (Phase 4).

**Exit criteria:** full run PM → Architect → Backend → QA → Docs (AC-03); interrupted run
resumes without repeating steps; timed-out agent leaves partial artifacts, run marked
`timeout`.

**Open items to resolve at planning:** the **runs/exports table gap** finally bites here —
resumable runs need a run-level record (agent_runs is per-agent). Will propose a `runs` table
(migration 0003) + wire router token/cost persistence. Also: real LLM calls are mocked in
tests; MVP path targets AC-03's PM→Architect→Backend→QA→Docs (QA included).

---

## How to run things

```bash
docker compose -f docker/docker-compose.yml up -d      # infra (or: make up)
./.venv/Scripts/python.exe -m pytest -q                # tests (venv has deps)
./.venv/Scripts/ruff.exe check . && ./.venv/Scripts/mypy.exe   # lint + types
cd apps/api && ../../.venv/Scripts/alembic.exe upgrade head    # migrations
```

Docker Desktop must be running for infra. Integration tests skip cleanly if it isn't.



