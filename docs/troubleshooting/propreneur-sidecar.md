# Propreneur sidecar troubleshooting

Keprix exposes a **propreneur** product pack under the shared product sidecar (`/v1/products/propreneur/...`). Propreneur Laravel remains authorization and data authority. Keprix calls allowlisted `/api/aiva/v1` routes with `TrustedExecutionContext` (workspace, actor, grants, Host, Authorization). Shared-token bootstrap is deprecated compatibility only.

Operator UI: `/settings/sidecars/propreneur` (pack readiness). Universal Sidecar `/settings/sidecars` is connectivity pairing only; do not equate it with CRUD readiness.

Machine readiness: `GET /v1/products/propreneur/readiness` (also nested under `/health`).

## Honesty (2026-08-09, prompts 636-643)

Engine connectivity and Aiva v1 domain CRUD via pack invoke are built for live reads and Soft Wall writes. Safe full CRUD means domain API access, Soft Wall, idempotency, and grants; not raw SQL, hard delete, or generic proxy.

- Capability honesty: `live`, `approval_required`, `proposal_only`, `not_configured`, `degraded`, `intentionally_forbidden`.
- Executable today: live reads + approval_required mutates/archives after Soft Wall (see evidence JSON).
- Still not agent-callable as product mutate: nested tasks/notes (`not_configured`), finance payment post, document binary vault, outbound communications send, hard delete, generic proxy (`intentionally_forbidden`).
- Proposal-only: compliance/finance proposals and elevated team invite drafts.
- Canonical matrix: `propreneur/docs/aiva/CRUD-COVERAGE-MATRIX.md`
- Evidence: `docs/architecture/propreneur-e2e-evidence.v1.json`
- Gap history: `docs/architecture/propreneur-crud-remediation-gap-report.md` (superseded claims annotated there)

If an older RAG chunk says all pack nodes are `not_configured`, treat that as superseded by this note and the readiness endpoint.

## Symptom: Operator sees healthy Universal Sidecar but agent CRUD fails

**Fix:** Open `/settings/sidecars/propreneur`. Check `crud_complete`, `capability_honesty`, pending approvals, circuit, `force_carina` / `outbound_kill`, and connector env `PROPRENEUR_PRODUCT_API_URL`. Connectivity != pack readiness.

## Symptom: Propreneur chat cannot use tools

**Fix:** Confirm engine is `keprix`, Aiva grant scopes cover the node, TrustedExecutionContext carries workspace/actor (fail-closed; no first-user fallback), and Host maps to the tenant subdomain.

## Symptom: Mutation hangs after Soft Wall approve

**Fix:** Use the same `approval_id` and input digest. Check idempotency key reuse, If-Match etag conflicts, circuit open, grant revoke/expiry, and execution receipts at `GET /v1/products/propreneur/receipts?workspace_id=...`. See `docs/architecture/propreneur-approvals-idempotency-events.md`.

## Symptom: Failed callback / ProductApiConnector error

**Fix:** Diagnose with `correlation_id`, Soft Wall `approval_id`, circuit state, connector host allowlist, grant scopes, and Laravel Aiva v1 response. Do not retry ambiguous writes through a second engine.

## Symptom: Agent asks to hard-delete or send outbound mail

**Expected denial.** Those operations are `intentionally_forbidden`. Tell the operator to use the Propreneur UI for vault binaries, payments, and messaging.

## Symptom: Circuit open / Keprix unavailable

**Fix:** Health-check Keprix; wait for circuit cooldown; use emergency disable / native engine only when policy allows pre-mutation fallback (`/v1/products/propreneur/admin/kill`).

## Related docs

- [Propreneur sidecar README](../propreneur-sidecar/README.md)
- [Approvals / idempotency / events](../architecture/propreneur-approvals-idempotency-events.md)
- [Trusted identity connector](../architecture/propreneur-connector-trusted-identity.md)
- [E2E testing](../architecture/propreneur-e2e-testing.md)
- [Key rotation](../propreneur-sidecar/key-rotation.md)
- [Observability runbook](../propreneur-sidecar/observability-runbook.md)
- [Canary cutover](../propreneur-sidecar/canary-cutover-rollback.md)
- [Release manifest](../operations/propreneur-sidecar-release-manifest.md)
- [Universal sidecar troubleshooting](../universal-sidecar/troubleshooting.md)
