# GenesisAI

From a plain-English product idea to production-ready software: prompts, architecture,
code, docs, tests, and CI. See [`docs/PRD.md`](docs/PRD.md) and [`docs/SRS.md`](docs/SRS.md).

## Stack

Next.js / React / TypeScript / Tailwind / shadcn (web) · FastAPI / Python 3.11+ (api) ·
PostgreSQL (Supabase) · Redis · LangGraph / LangChain · ChromaDB.

## Layout

```
apps/web      Next.js frontend        packages/agents   agent graphs (Phase 5)
apps/api      FastAPI backend         packages/router   LLM routing (Phase 2)
docker/       compose + Dockerfiles   packages/memory   context memory (Phase 3)
scripts/      setup / migrate / seed  packages/shared   shared TS types
tests/        cross-package tests     docs/             PRD, SRS, architecture
```

## Prerequisites

Docker, Python 3.11+, Node 20+, `pnpm` (`corepack enable`). `make` optional — every
target below has a raw-command equivalent.

## Quickstart

```bash
cp .env.example .env         # fill in as needed; defaults work for local infra
make up                      # start Postgres, Redis, ChromaDB   (docker compose -f docker/docker-compose.yml up -d)
make install                 # pip install -e apps/api -r requirements-dev.txt ; pnpm install
make dev                     # prints how to run api + web (separate terminals)
```

- API:  `cd apps/api && uvicorn app.main:app --reload --port 8000` → http://localhost:8000/health
- Web:  `pnpm --filter web dev` → http://localhost:3000

## Checks

```bash
make lint        # ruff check . ; pnpm --filter web lint
make typecheck   # mypy ; tsc --noEmit
make test        # pytest
```

Optional pre-commit hooks: `pip install pre-commit && pre-commit install`.

## Phases

Built in order per the implementation brief; each phase stops for review. Phase 0
(this) is scaffolding + tooling only — no business logic beyond `/health`.
