# Acceptance Criteria verification (SRS §12)

Evidence for AC-01 through AC-08. "Verified" means a test asserts it in this repo; where a
criterion needs a deployed stack or real provider keys, that is stated plainly rather than
claimed.

| # | Criterion | Status | Evidence |
|---|---|---|---|
| AC-01 | Optimized prompts from a plain-English idea, scored above threshold | Verified | `packages/agents/tests/test_optimizer.py::test_all_sample_ideas_reach_threshold` (20 ideas ≥ 0.8) |
| AC-02 | Project context maintained across agents | Verified | `packages/memory/tests/test_memory.py::test_later_agent_recalls_earlier_decision` |
| AC-03 | Agents coordinated end to end (PM → Architect → Backend → QA → Docs) | Verified | `packages/agents/tests/test_workflow.py::test_full_run_completes_in_order`; `apps/api/tests/test_orchestrator.py::test_full_run_records_steps_and_status` |
| AC-04 | Exported project installs, builds, passes its generated tests | Verified | `apps/api/tests/test_export_service.py::test_exported_project_builds_and_passes_in_container` (real `docker build` + `docker run`) |
| AC-05 | Same project runs on ≥ 3 providers | Verified (deterministic) | `packages/router/tests/test_multi_provider.py` (openai, deepseek, gemini). Live end-to-end confirmation needs real provider keys. |
| AC-06 | Export contains source, tests, Docker, CI, README | Verified | `apps/api/tests/test_export_service.py` (contents asserted after extraction) |
| AC-07 | Meets performance targets (§8) | Partial | Sequential read p95 < 300ms: `apps/api/tests/test_latency.py` (passes). Concurrency: `scripts/loadtest.py` is functional; a **single local dev worker** at concurrency 200 measured p95 ~8.5s (client and server sharing one machine, one process). This confirms the 1,000-user budget requires the deployed multi-worker + autoscaled topology (§11), not a single process. Run `scripts/loadtest.py --url <deployed> --concurrency 1000` there. |
| AC-08 | API keys never appear in logs, responses, or exports | Verified | Responses/logs: `apps/api/tests/test_key_never_leaks.py`. Exports: `apps/api/tests/test_security_export.py`. |

## Non-functional coverage

- **NFR-02** prompt latency < 5s p95: `test_optimizer.py::test_latency_budget_p95_under_5s`.
- **NFR-03 / AC-08** key encryption at rest, never returned: `test_crypto.py`, `test_key_never_leaks.py`.
- **NFR-09** exports carry no GenesisAI dependency: `test_export_service.py` (no `genesis` reference).
- **§7 audit logging**: auth events, key changes, and exports are written to `logs`; read surface at
  `GET /logs` (admin), `test_logs_api.py`.

## Honest gaps (need a deployed environment or real keys)

- **AC-07 at 1,000 concurrent users**: requires deployed, scaled API + workers. Harness provided.
- **AC-05 live run**: requires real provider keys; the routing/fallback capability is proven with
  fakes, and a full agent run needs a key added via the Keys screen (FR-14).
- **CI on GitHub Actions**: workflow is present and mirrors local checks; not exercised remotely here.
