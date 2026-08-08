# Prompt PTS-02: Petraclus service API and authorised read connector

## What was built

- `connector/fixture_product_api.py` + `connector/manifest.yaml` (default deny)
- Reads, proposals, gated actions with approval hash and idempotency
- Workspace-scoped fixtures ws-alpha/ws-beta/ws-team


**Status: COMPLETED 2026-08-08**
**Depends on:** PTS-00, PTS-01
**Blocks:** PTS-03 through PTS-05

## Goal

Open a least-privilege Petraclus service API and implement its Keprix connector.

## Product endpoints

1. Common health, capabilities, token exchange, context and event acknowledgement.
2. Reads: `/workspaces/{id}`, `/assets`, `/assets/{id}`, `/target-grants/{id}`,
   `/scans`, `/scans/{id}`, `/findings`, `/findings/{id}`, redacted `/evidence`,
   `/reports`, `/audit`, `/retention-policy`, `/licence/effective-entitlements`.
3. Proposals: `/scan-plans/validate`, `/finding-changes/preview`,
   `/remediation/preview`, `/reports/preview`, `/tickets/preview`.
4. Actions: `/scans/start`, `/scans/{id}/cancel`, `/findings/{id}/transition`,
   `/reports/{id}/publish`, `/tickets/create`; require approval hash and idempotency.
5. Cursor pagination, field projection, stable filters and response schemas.
   Evidence defaults redacted; raw retrieval needs a narrower grant and audit reason.

## Connector requirements

1. Typed client with strict TLS, short timeouts, response size caps, schema checks,
   retry only for safe/idempotent calls, circuit breaker and correlation ids.
2. Resolve target hostnames product-side, reject internal/link-local/metadata ranges
   unless the signed grant explicitly names them, and pin resolution per action.
3. Map 401, 403, 404, 409, 422, 429 and dependency errors into honest tool states.
4. Never log tokens, findings, raw evidence, credentials or target inventories.
5. Contract tests prove workspace scoping, edition gates, projections, redaction,
   stale approval rejection, target revocation and duplicate-action prevention.

## Acceptance

- [x] Keprix reads only declared projected endpoints
- [x] Product revalidates licence, target and approval on writes
- [x] Direct SQL and UI scraping are absent
- [x] Raw evidence and secrets stay out of logs and default prompts
