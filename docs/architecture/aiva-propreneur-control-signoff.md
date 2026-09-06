# Aiva-Propreneur control programme sign-off

**Date:** 2026-08-09  
**Scope:** Programme prompts 20-26 (`keprix-propreneur-aiva-three-way/20-aiva-propreneur-control`)  
**Contabo deploy:** not performed (owner-gated for this programme)

## Verdict: PARTIAL (automated canary GREEN)

Honest evidence:

- **Automated canary:** `AUTOMATED_CANARY_GREEN` via `propreneur/scripts/aiva-propreneur-control-canary.sh` (10/10 Pest+Vitest steps on 2026-08-09).
- **General release / Contabo:** still **PARTIAL** until owner signs restricted cohort + Contabo cutover.

### What is evidenced (prompts 20-26)

| Prompt | Evidence |
| --- | --- |
| 20 Identity | PKCE S256, grants, channel bind/unbind Pest |
| 21 CRUD v1 | Matrix + OpenAPI tools + isolation/conflict/pagination Pest |
| 22 Tools / behaviour | Contract 1.1, channel digests, behaviour evals |
| 23 Sync | Outbox catalogue enqueue, inbox reconcile/replay/conflicts |
| 24 Risk | Digests always bound, dual-control thresholds, pause, anomaly, runbook |
| 25 Control UX | Connection, matrix, timeline, sync (archived earlier) |
| 26 Canary | Runner + security/performance reports + results artefact |

### What blocks general-release READY

1. Owner named-account canary on a restricted tenant cohort (runbook steps in `propreneur/docs/aiva/CANARY-AND-SIGNOFF.md`).
2. Contabo cutover not done; do not assume live Clinicom/Carina flips.
3. Live Telegram bot cohort not proven (code path is digest-bound).
4. CRUD matrix `gap`/`bridge` domains must stay out of "complete" marketing claims.
5. Prefer `propreneur_testing_agent` for Pest when `propreneur_testing` lacks `public` schema.

## Linked artefacts

| Artefact | Path |
| --- | --- |
| Canary runbook + sign-off | `propreneur/docs/aiva/CANARY-AND-SIGNOFF.md` |
| Canary results (latest) | `propreneur/docs/aiva/CANARY-RESULTS-latest.md` |
| Security report | `propreneur/docs/aiva/CANARY-SECURITY-REPORT.md` |
| Performance report | `propreneur/docs/aiva/CANARY-PERFORMANCE-REPORT.md` |
| CRUD matrix | `propreneur/docs/aiva/CRUD-COVERAGE-MATRIX.md` |
| Identity model | `propreneur/docs/aiva/IDENTITY-GRANT-MODEL.md` |
| High-risk / incident | `propreneur/docs/aiva/HIGH-RISK-APPROVALS-AND-INCIDENT.md` |
| Domain pack | `keprix/domain-packs/propreneur/` |
| Canary script | `propreneur/scripts/aiva-propreneur-control-canary.sh` |

## Owner action required for READY

1. Run owner canary runbook steps on internal accounts.
2. Confirm no cross-tenant leakage in production-like envs.
3. Decide Contabo cutover separately; keep Carina sidecar live for Clinicom until an explicit flip.
4. Record owner + product rows in the sign-off table.

## Correction (2026-08-09, prompt 636)

Historical PARTIAL verdict and canary evidence above remain valid for scaffolding and Aiva v1 Pest coverage. Appended honesty note:

- Do not treat pack capability labels or prior "CRUD v1" matrix rows as proof that Keprix product-pack invoke executes full Propreneur CRUD.
- Engine connectivity is built; complete agent CRUD through product-pack handlers is under remediation (`keprix-propreneur-crud-remediation`).
- Gap report: `keprix/docs/architecture/propreneur-crud-remediation-gap-report.json`
- Fail-closed rule: nodes without handlers report `not_configured` / `degraded`, never `live`.
