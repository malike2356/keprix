# Carina/Aiva Keprix sidecar sign-off

**Status:** READY (local programme)
**Date:** 2026-08-08
**Writing style:** plain ASCII only.

## Verdict: READY for capped local/staging pilot

Carina and Aiva can consume Keprix through `/v1/products/{carina|aiva}` with an
advertised capability catalog, Soft Wall ownership on the product, southbound
allowlist, short-lived tokens (shared-token compat deprecated), shadow path,
circuit/idempotency, OPS invoke honesty probe, and automated isolation tests.

## Shipped (CAS-00..15 core)

- Gap map + boundary lock
- Packs `carina` + `aiva` wrapper
- Northbound health/capabilities/manifest/sessions/invoke/jobs/events/approvals/metrics
- Legacy `POST /carina/agent/run` remains
- Southbound connector + Carina `/api/keprix/v1/*`
- Token exchange + grant matrix
- Shadow dual-run node behaviour
- CRM / Soft Wall / viCal / Scout hooks / memory / RAG / jobs / playbooks / data nodes
- Soft Wall deep links; approval resume
- Memory authority + retention delete
- OPS primary invoke probe (not health-only)
- Security contract tests + residual risk list

## Deferred (owner-gated Nice)

- `crm.enrich.licensed` live keys
- WhatsApp / SMS live keys
- Social OAuth publish
- Broad default-on for all non-admin workspaces (needs pilot thresholds)

## Pilot plan (capped)

1. Internal workspace only; Soft Wall on for all outbound.
2. Shadow flag first; then opted primary; then default-on non-admin after thresholds.
3. Kill: pack disable, `force_carina`, outbound kill.
4. Rollback: OPS emergency-rollback to Carina engine + pack disable.
5. Contabo: if touched, verify `https://carinaai.uk/` returns 200.

## Rollback drill

1. `POST /v1/products/carina/admin/kill` action `force_carina`.
2. OPS emergency-rollback / global_engine=carina.
3. Confirm legacy bridge still serves chat.
4. Confirm no duplicate outbox via idempotency keys.

## Soft separation checklist

- [x] No second Aiva Python/TS agent runtime
- [x] Aiva pack is wrapper metadata + entitlement filter
- [x] Shared nodes execute carina handler family
- [x] No nested `carina/verlox/`
- [x] Stripe: no new prices (SKU labels only)

## Archive

Archive CAS pending prompts to `prompts-archive/keprix-sidecar-carina-aiva/` when
this READY verdict is accepted in-session.
