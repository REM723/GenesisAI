# GenesisAI — Build Progress Tracker

**Purpose:** single source of truth for what's done, what's next, and the decisions made.
Re-read this at the start of every session/phase. Update it at the end of every phase.
Authoritative specs remain `docs/PRD.md` and `docs/SRS.md`; this only tracks execution.

**Last updated:** 2026-07-26 (end of Phase 7)
**Current position:** Phase 7 complete and reviewed. Phase 8 not yet started.
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
| 5 | Agent workflow (LangGraph) | ✅ Done |
| 6 | API surface | ✅ Done |
| 7 | Frontend | ✅ Done |
| 8 | Export + doc generation | ⏳ Next |
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

## Phase 5 — Agent workflow (LangGraph) ✅

`packages/agents/genesis_agents`: `agents.py` (7 AgentSpecs + `AgentRunner` + `RouterAgentRunner`),
`review.py`, `workflow.py` (LangGraph StateGraph, per-agent timeouts, retry edges after
backend/frontend, MemorySaver). `apps/api`: `Run` model + `run_id` on `agent_runs` (migration
`0003`), `RunRepository`/`AgentRunRepository`, `app/orchestrator.py`, `app/agents_api.py` (SSE).
Added `langgraph`.

**Decisions:** graph DB-free; orchestrator's injected `on_event` owns side effects (agent_runs,
memory, Redis SSE, run status); resume via checkpointer (thread=run_id); reviewer returns work
once (MAX_ATTEMPTS=2); SSE over Redis pub/sub; runner injected (faked in tests, no live calls).

**Verified:** graph-level AC-03/resume/timeout/reviewer offline; orchestrator (live PG+Redis)
full run records steps+status, timeout marks run + keeps partial, SSE published/consumed.
Migrations 0001–0003 up/down/up clean (head `0003_runs`). ruff/mypy strict clean. Suite: 39.

**Resolved:** runs-table gap (0003). **Deferred:** `exports` table → Phase 8; router token/cost
persistence (orchestrator writes tokens=0 until the router-backed runner returns usage);
cross-process resume needs a persistent LangGraph saver (MemorySaver is in-process).

## Phase 6 — API surface ✅

`apps/api`: `app/ratelimit.py` (Redis fixed-window, per user+IP, 429+Retry-After),
`app/pagination.py` (opaque keyset cursor), `app/projects_api.py`, `app/prompts_api.py`,
`app/artifacts_api.py` (code/review, tests/generate, exports), `POST /agents/run` in
`agents_api.py`; `ProjectRepository`/`GeneratedCodeRepository`/`DocumentRepository` + read
methods; schemas for all §9 bodies. No migration (no schema change).

**Decisions:** hand-rolled Redis rate limiting (no dep); `POST /agents/run` launches the
orchestrator as a background asyncio task → `202 + run_id` (resume if run_id given); added
`GET /projects` (list, cursor-paginated) as a documented §9 divergence for FR-02; `/code/review`
+ `/tests/generate` thin (reviewer / single QA call over stored code); `GET /exports/{id}` wired
but `404` until Phase 8 packaging.

**Verified:** contract tests for every §9 endpoint (shapes/status/auth/422); pagination shape;
`202 + run_id`; OpenAPI exposes all §9 paths; rate-limit counter blocks past limit and HTTP
returns `429 + Retry-After`. ruff/mypy strict clean (36 files). Full suite: 47 passed.

**Deferred:** real background job queue/worker (asyncio task for MVP; Redis queue is the
upgrade); `/exports` behavior → Phase 8; wiring real provider keys for live `/agents/run`.

## Phase 7 — Frontend ✅

`apps/web`: design system in `globals.css` + `tailwind.config.ts` (warm near-black palette,
custom ease-out curves, serif display, focus/selection treatment, stagger keyframes). Typed
client `lib/api.ts`, auth provider `lib/auth.tsx`, SSE-over-fetch hook `lib/run-stream.ts`.
Primitives (`button`/`input`/`card`/`spinner`), `status-badge`, `wordmark`, `app-nav`,
`auth-form`, `run-timeline`. Routes: landing `/`, `/login`, `/signup`, and an authed `(app)`
group with `/dashboard`, `/projects/new`, `/projects/[id]`, `/settings/keys`.

**Design (via /emil-design-eng):** press feedback `scale(0.97)`, motion under 300ms with custom
ease-out, staggered list entrance (45ms), pulse only on active status, brisk 640ms spinner,
`prefers-reduced-motion` respected. No emoji, no em dashes in copy, restrained brass accent used
sparingly. System font stack (no network font fetch) for a guaranteed clean build.

**Decisions:** hand-written typed API client (OpenAPI codegen is the upgrade); localStorage
tokens (httpOnly cookies are the hardening upgrade, need a backend contract change); SSE consumed
via `fetch` + `ReadableStream` because `EventSource` cannot send the bearer header.

**Verified:** `tsc --noEmit` clean, `next lint` clean, `prettier --check` clean, `next build`
green (9 routes), prod server serves 200. **Not verified here:** the live click-through — the
Chrome extension is not connected in this environment, and a *successful* agent run additionally
needs a real provider key (added via the Keys screen, FR-14). The client is wired end-to-end to
the §9 API; export download is a graceful "coming next release" state until Phase 8.

**Deferred:** live E2E walkthrough (needs a browser + provider key); export button real download
(Phase 8); token auto-refresh on 401 (client currently uses the access token directly).

## Phase 8 — Export + documentation generation ⏳ (next)

**Goal (NFR-09, AC-04/AC-06):** package a generated project (source, tests, Dockerfile, CI, README)
into a downloadable archive with no GenesisAI runtime dependency; re-export without re-running
agents; wire `GET /exports/{id}` to serve it and the frontend export button to download it.

**Exit criteria:** an exported project installs, builds, and passes its own generated tests in a
clean container (AC-04, AC-06).

**Open items at planning:** where export artifacts live (an `exports` table + object storage vs.
zip-on-the-fly from stored `generated_code`/`documents`); how AC-04/06 are tested in this
environment (Docker is available; building a generated project in a container is the check).

---

## How to run things

```bash
docker compose -f docker/docker-compose.yml up -d      # infra (or: make up)
./.venv/Scripts/python.exe -m pytest -q                # tests (venv has deps)
./.venv/Scripts/ruff.exe check . && ./.venv/Scripts/mypy.exe   # lint + types
cd apps/api && ../../.venv/Scripts/alembic.exe upgrade head    # migrations
```

Docker Desktop must be running for infra. Integration tests skip cleanly if it isn't.



