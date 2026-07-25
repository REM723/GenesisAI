# GenesisAI — Software Requirements Specification

| Field | Value |
|---|---|
| Product | GenesisAI |
| Document | Software Requirements Specification (SRS) |
| Version | 1.0 |
| Status | Draft |
| Owner | Ryan |
| Last updated | 2026-07-25 |
| Companion doc | [PRD.md](./PRD.md) |

---

## 1. Purpose

GenesisAI automates software engineering by transforming business ideas into optimized prompts, architecture, code, documentation, tests, and deployment pipelines.

This document defines the system architecture, technology stack, data model, interfaces, security model, and acceptance criteria required to build it.

### Scope

Covers the GenesisAI platform: web client, API, orchestrator, agent layer, model router, and persistence. Does not cover the runtime operation of applications generated *by* GenesisAI — those are exported and run by the user.

### Definitions

| Term | Meaning |
|---|---|
| Agent | A specialized LLM-driven worker with a fixed role and toolset |
| Run | One execution of a workflow across agents for a project |
| Artifact | Any generated output: prompt, code file, doc, test, config |
| Router | Component selecting which LLM serves a given task |
| Context Memory | Per-project store of requirements, decisions, and artifacts |

---

## 2. System Architecture

```text
                        ┌──────────────┐
                        │     User     │
                        └──────┬───────┘
                               │ HTTPS
                        ┌──────▼───────┐
                        │  Next.js /   │
                        │    React     │   Vercel
                        └──────┬───────┘
                               │ REST + SSE
                        ┌──────▼───────┐
                        │   FastAPI    │   API gateway, auth, validation
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │   Workflow   │   Job queue, state machine,
                        │ Orchestrator │   retries, timeouts
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │  LangGraph / │
                        │  LangChain   │
                        └──────┬───────┘
                               │
   ┌──────────┬──────────┬─────┴────┬──────────┬──────────┬──────────┐
   ▼          ▼          ▼          ▼          ▼          ▼          ▼
 Product   Architect  Backend   Frontend     QA       DevOps      Docs
 Manager    Agent      Agent      Agent     Agent      Agent      Agent
 Agent
   └──────────┴──────────┴─────┬────┴──────────┴──────────┴──────────┘
                               │
                        ┌──────▼───────┐
                        │  LLM Router  │   cost / latency / capability
                        └──────┬───────┘
                               │
        ┌─────────┬────────┬───┴────┬─────────┬──────────┐
        ▼         ▼        ▼        ▼         ▼          ▼
     OpenAI     Grok    Gemini   Ollama   DeepSeek   OpenRouter

                        ┌──────────────┐
                        │  PostgreSQL  │  relational state
                        │    Redis     │  queue, cache, rate limits
                        │   Storage    │  artifacts, exports
                        │  ChromaDB    │  vector context memory
                        └──────────────┘
```

### Components

| Component | Responsibility |
|---|---|
| Web client | Project UI, run monitoring, artifact preview, export download |
| API (FastAPI) | AuthN/AuthZ, request validation, rate limiting, run lifecycle |
| Orchestrator | Schedules agent steps, persists checkpoints, enforces timeouts |
| Agent layer | Role-specific reasoning and artifact production |
| LLM Router | Provider selection, fallback, token accounting |
| Context Memory | Vector + relational retrieval of project context for agents |
| Artifact Store | Versioned storage of generated files; zip packaging for export |

---

## 3. Technology Stack

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui

### Backend

- FastAPI
- Python 3.11+

### Database

- PostgreSQL (Supabase)
- Redis — queue, cache, rate limiting

### AI framework

- LangGraph — stateful agent graphs
- LangChain — tool and provider abstractions

### Vector database

- ChromaDB (dev) / FAISS (embedded) — pluggable interface

### Deployment

- Vercel — frontend
- Railway / Render / Fly.io — API and workers
- Docker — local dev and portable deploys

---

## 4. Supported LLM Providers

| Provider | Role |
|---|---|
| Grok | General reasoning |
| OpenAI | General reasoning, code |
| Gemini | Long context, multimodal |
| DeepSeek | Cost-efficient code generation |
| Mistral | Cost-efficient general tasks |
| OpenRouter | Aggregated fallback access |
| Ollama | Local / offline / private inference |

**Routing policy:** each agent declares required capabilities (context length, code strength, tool use, cost ceiling). The router picks the cheapest provider meeting the requirement, with an ordered fallback chain on error, timeout, or rate limit.

---

## 5. Data Model

### Tables

| Table | Purpose | Key fields |
|---|---|---|
| `users` | Account records | `id`, `email`, `password_hash`, `role`, `created_at` |
| `projects` | One product idea per row | `id`, `user_id`, `name`, `idea`, `status`, `created_at` |
| `prompts` | Current prompt per project task | `id`, `project_id`, `type`, `content`, `score` |
| `prompt_versions` | Full prompt history | `id`, `prompt_id`, `version`, `content`, `score`, `created_at` |
| `generated_code` | Code artifacts | `id`, `project_id`, `path`, `language`, `content`, `version` |
| `documents` | Docs artifacts | `id`, `project_id`, `type`, `content`, `version` |
| `agent_runs` | Execution records | `id`, `project_id`, `agent`, `status`, `input`, `output`, `tokens`, `duration_ms` |
| `api_keys` | BYO provider keys | `id`, `user_id`, `provider`, `encrypted_key`, `created_at` |
| `settings` | Per-user / per-project prefs | `id`, `scope`, `scope_id`, `key`, `value` |
| `logs` | Audit and system events | `id`, `user_id`, `event`, `payload`, `created_at` |

### Relationships

```text
users 1──∞ projects 1──∞ prompts 1──∞ prompt_versions
                    1──∞ generated_code
                    1──∞ documents
                    1──∞ agent_runs
users 1──∞ api_keys
users 1──∞ logs
```

### Constraints

- `projects.status` ∈ `{draft, analyzing, running, completed, failed}`
- `agent_runs.status` ∈ `{queued, running, succeeded, failed, timeout}`
- `api_keys.encrypted_key` is write-only via API; never returned in responses
- Cascade delete: removing a project removes its prompts, code, docs, and runs

---

## 6. Agent Workflow

```text
Idea
  ↓
Requirement Analysis      Product Manager Agent
  ↓
Architecture Planning     Architect Agent
  ↓
Prompt Optimization       Prompt Optimizer + Loop Engine
  ↓
Task Breakdown            Architect Agent
  ↓
Code Generation           Backend Agent + Frontend Agent
  ↓
Testing                   QA Agent
  ↓
Documentation             Documentation Agent
  ↓
Deployment                DevOps Agent
  ↓
Export
```

### Agent responsibilities

| Agent | Input | Output |
|---|---|---|
| Product Manager | Raw idea or PRD | Structured requirements, user stories, scope |
| Architect | Requirements | Architecture, stack choice, module boundaries, task list |
| Backend | Task list, architecture | API code, models, migrations |
| Frontend | Task list, architecture | Pages, components, state, styling |
| QA | Generated code | Unit and integration tests, defect report |
| DevOps | Repo structure | Dockerfile, CI workflow, deployment guide |
| Documentation | All artifacts | README, API docs, architecture doc, setup guide |

### Execution rules

- Each step reads from and writes to Context Memory — no agent re-derives prior context.
- Steps are checkpointed; a failed run resumes from the last successful step.
- Per-agent timeout applies (see §8). On timeout, the run is marked `timeout` and partial artifacts are retained.
- The Code Reviewer gate runs after code generation; a failing gate returns work to the generating agent once before surfacing to the user.

---

## 7. Security

| Control | Implementation |
|---|---|
| Authentication | JWT access tokens + refresh tokens; short access TTL |
| Authorization | RBAC — roles: `owner`, `member`, `admin` |
| Transport | HTTPS only; HSTS; secure cookies |
| API key protection | Encrypted at rest (AES-GCM); decrypted in memory only at call time; never logged or returned |
| Rate limiting | Per user and per IP, enforced in Redis |
| Audit logging | All auth events, key changes, exports, and destructive actions |
| Input validation | Pydantic schemas on every endpoint; file type and size limits on uploads |
| Prompt injection defense | Untrusted input sanitized and fenced; agent tool scopes least-privilege; outputs schema-validated |
| Secret handling | Environment-based config; no secrets in repo or generated artifacts |

---

## 8. Performance

| Operation | Target |
|---|---|
| Prompt generation | < 5 s |
| Agent workflow (MVP path) | < 15 s |
| Documentation generation | < 10 s |
| Export packaging | < 10 s |
| API read endpoints | < 300 ms (p95, excluding LLM calls) |
| Concurrent users | 1,000 |

Targets are p95 excluding user-side network. LLM-bound operations depend on provider latency; the router deprioritizes providers exceeding the budget.

---

## 9. API

### Endpoints

```http
POST   /projects                 Create project from an idea
GET    /projects/{id}            Fetch project with artifacts and run status
POST   /prompts/generate         Generate optimized prompts for a project
POST   /agents/run               Start or resume an agent workflow run
POST   /code/review              Run the Code Reviewer over generated code
POST   /tests/generate           Generate tests for generated code
GET    /exports/{id}             Download packaged project export
```

### Conventions

- All endpoints require `Authorization: Bearer <jwt>` except auth routes.
- Request and response bodies are JSON; validation errors return `422` with field detail.
- Long-running operations return `202 Accepted` with a `run_id`; progress streams over SSE at `GET /agents/runs/{run_id}/stream`.
- All list endpoints are cursor-paginated.

### Example

```http
POST /projects
Content-Type: application/json

{
  "name": "Habit tracker",
  "idea": "A mobile-first habit tracker with streaks and weekly email summaries."
}
```

```json
{
  "id": "prj_01H...",
  "status": "analyzing",
  "created_at": "2026-07-25T10:04:11Z"
}
```

---

## 10. Error Handling

| Condition | HTTP | Behavior |
|---|---|---|
| Invalid or missing API key | 401 | Reject; prompt user to add a provider key |
| Provider rejects key | 402 / 403 | Surface provider message; do not retry blindly |
| Agent timeout | 504 | Mark run `timeout`; retain partial artifacts; offer resume |
| Model unavailable | 503 | Router falls back to next provider; log the switch |
| Prompt validation failure | 422 | Return failed constraints; re-run optimizer loop |
| Database failure | 500 | Retry with backoff; fail run cleanly; alert |
| Export failure | 500 | Retain artifacts; allow re-export without re-running agents |
| Rate limit exceeded | 429 | Return `Retry-After` |

**Principles:** fail loudly to logs, softly to the user; never lose generated artifacts on failure; every error carries a correlation ID linking API request, run, and agent step.

---

## 11. Deployment

```text
Client
  ↓
Vercel            Next.js frontend
  ↓
FastAPI           API + workers (Railway / Render / Fly.io)
  ↓
Redis             queue, cache, rate limits
  ↓
LangGraph         agent execution
  ↓
Supabase          PostgreSQL + storage
  ↓
LLM Providers     OpenAI / Grok / Gemini / DeepSeek / Mistral / OpenRouter / Ollama
```

### Environments

| Environment | Purpose |
|---|---|
| local | Docker Compose: API, Postgres, Redis, Chroma, Ollama |
| staging | Full stack, seeded data, non-production keys |
| production | Autoscaled API and workers, managed Postgres and Redis |

### CI/CD

- Pull request: lint, type-check, unit tests, build
- Merge to `main`: build images, run migrations, deploy staging
- Tagged release: promote to production, smoke test, auto-rollback on failure

---

## 12. Acceptance Criteria

| # | Criterion | Verification |
|---|---|---|
| AC-01 | Generates optimized prompts from a plain-English idea | Optimizer returns scored prompts above threshold for 20 sample ideas |
| AC-02 | Maintains project context across agents | Later agents reference earlier decisions without re-supplied input |
| AC-03 | Coordinates AI agents end to end | A full run completes PM → Architect → Backend → QA → Docs |
| AC-04 | Produces production-ready artifacts | Exported project installs, builds, and passes its generated tests |
| AC-05 | Supports multiple LLM providers | Same project runs successfully on at least three providers |
| AC-06 | Exports complete projects | `.zip` contains source, tests, Docker, CI config, and README |
| AC-07 | Meets performance targets | Load test at 1,000 concurrent users within §8 budgets |
| AC-08 | Meets security requirements | API keys never appear in logs, responses, or exports |

---

## 13. Repository Structure

```text
genesisai/
├── apps/
│   ├── web/                 Next.js frontend
│   └── api/                 FastAPI backend
├── packages/
│   ├── agents/              Agent definitions and graphs
│   ├── router/              LLM routing and provider adapters
│   ├── memory/              Context memory and vector store
│   └── shared/              Types, schemas, utilities
├── docs/
│   ├── PRD.md
│   ├── SRS.md
│   └── architecture/
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.web
│   └── docker-compose.yml
├── scripts/                 Setup, migration, seed scripts
├── tests/                   Cross-package integration tests
└── README.md
```

---

## Related documents

- [Product Requirements Document](./PRD.md)
