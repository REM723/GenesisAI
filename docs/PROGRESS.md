# GenesisAI — Build Progress Tracker

**Purpose:** single source of truth for what's done, what's next, and the decisions made.
Re-read this at the start of every session/phase. Update it at the end of every phase.
Authoritative specs remain `docs/PRD.md` and `docs/SRS.md`; this only tracks execution.

**Last updated:** 2026-07-25 (end of Phase 2)
**Current position:** Phase 2 complete and reviewed. Phase 3 not yet started.

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
| 3 | Context memory | ⏳ Next |
| 4 | Prompt optimizer + loop engine | ⬜ Not started |
| 5 | Agent workflow (LangGraph) | ⬜ Not started |
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

## Phase 3 — Context memory ⏳ (next)

**Goal (SRS §2/§3, AC-02):** per-project context store — relational records (requirements,
decisions, artifacts) + vector recall over ChromaDB. One read/write interface agents use;
no agent touches the DB or vector store directly. Lives in `packages/memory`.

**Exit criteria:** a later agent retrieves a decision made by an earlier agent without it
being re-supplied in the prompt (AC-02) — prove with a test.

**Likely open questions to raise at planning:** embedding model/source (needs a provider
key vs. a local/deterministic embedder for tests); whether memory writes reuse the Phase-1
tables (`documents`, plus a new decisions/requirements store) or a dedicated schema — a
schema question to flag before migrating.

---

## How to run things

```bash
docker compose -f docker/docker-compose.yml up -d      # infra (or: make up)
./.venv/Scripts/python.exe -m pytest -q                # tests (venv has deps)
./.venv/Scripts/ruff.exe check . && ./.venv/Scripts/mypy.exe   # lint + types
cd apps/api && ../../.venv/Scripts/alembic.exe upgrade head    # migrations
```

Docker Desktop must be running for infra. Integration tests skip cleanly if it isn't.



