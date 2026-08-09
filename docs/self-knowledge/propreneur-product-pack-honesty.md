# Propreneur product-pack capability honesty (self-knowledge)

**Updated:** 2026-08-09 (prompt 643)
**Audience:** Keprix agent, operator copilot, support RAG

## Source of truth

Propreneur Laravel domain services via `/api/aiva/v1` are the system of record.
Keprix is the Soft Wall, grant, idempotency, and product-pack invoke plane.
Safe full CRUD means domain API access under Soft Wall; not raw database access,
hard delete, binary vault I/O, payment posting, or a generic proxy.

Canonical workstation root: `/opt/lampp/htdocs/verlox/propreneur` (not `propreneur/propreneur-v2`).

## Can Keprix perform Propreneur CRUD?

Yes, for contracted live reads and Soft Wall gated writes/archives exposed by the
`propreneur` product pack and chat adapter. Operator readiness:
`GET /v1/products/propreneur/readiness` and UI `/settings/sidecars/propreneur`.

Do not treat Universal Sidecar project health or a bare HTTP 200 as CRUD readiness.

## What requires approval?

Operations with status `approval_required` (create/update/archive/cancel on
properties, contacts, deals, tenancies, maintenance, projects, sourcing, and
similar). Soft Wall approval digest is required; free-text "yes" is not enough.

## What is forbidden?

`intentionally_forbidden` contract ops include: hard delete, document binary
upload/download, finance payment post, outbound communications send, and generic
proxy. Agents must refuse and point operators to the Propreneur UI.

## What is still not configured?

Examples: nested task create, note create, sync_health, some appointment create
paths. Status `proposal_only` covers compliance/finance drafts and elevated
team invite proposals (not direct product mutate).

## How to diagnose a failed callback

1. Capture `correlation_id` and Soft Wall `approval_id`.
2. Check circuit state, `force_carina`, `outbound_kill`, grant revoke/expiry.
3. Check connector `PROPRENEUR_PRODUCT_API_URL`, host allowlist, and If-Match etag.
4. Inspect execution receipts and pending approvals on the readiness endpoint.
5. Prefer one engine; do not double-write through Carina and Keprix.

## Human docs that must agree

- `docs/propreneur-sidecar/README.md`
- `docs/troubleshooting/propreneur-sidecar.md`
- `docs/architecture/propreneur-approvals-idempotency-events.md`
- `docs/architecture/propreneur-connector-trusted-identity.md`
- `propreneur/docs/aiva/CRUD-COVERAGE-MATRIX.md`
- `domain-packs/propreneur/docs/propreneur-aiva-capability-guidance.md`
