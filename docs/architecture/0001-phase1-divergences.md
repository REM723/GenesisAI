# Phase 1 — divergences from the SRS

Recorded per the working agreement: note where implementation diverges from the spec
rather than silently editing it. None of these change a migrated schema or an existing
SRS §9 contract; they fill gaps the spec left open.

| # | Divergence | Rationale |
|---|---|---|
| 1 | Added `POST /auth/register\|login\|logout\|refresh` | FR-01 requires auth; SRS §9 lists no auth routes but assumes them ("all endpoints require Bearer except auth routes"). |
| 2 | Added `POST /keys`, `GET /keys` | FR-14 (BYO keys) needs per-user key management; §9 omits it. |
| 3 | Refresh-token state in Redis, not a new table | §5 has no refresh/session table; Redis (already in-stack for exactly this) gives TTL + revocation without a schema addition. |
| 4 | `users.role ∈ {admin, member}`; project "owner" = `projects.user_id` | §7 names `owner/member/admin` but §5 has a single `role` column and per-project membership is FR-16 (Future). Reconciled without inventing a membership table. |
| 5 | `logs.user_id` is `ON DELETE SET NULL` (not cascade) | §7 mandates audit logging; the trail should outlive the user. §5 only mandates *project* cascade. |
| 6 | Added `agent_runs.created_at` | Not in §5's field list, but run history needs deterministic ordering. |
| 7 | UUID primary keys (native `uuid`) | §9's `"prj_01H…"` example implies prefixed ULIDs. Treated as a presentation concern deferred to Phase 6; PK type stays `uuid` to avoid a later type migration. **Revisit at Phase 6 if the ID format is contractual.** |

## Still-open gap (not yet actioned)

SRS §9 references a run-level `/agents/runs/{run_id}` and `/exports/{id}`, but §5 has no
`runs` or `exports` table (`agent_runs` is per-agent). Resumable runs (§6) will need a
run-level record. Raised here; decision deferred to Phase 5/8 where it is first needed.
