# Prompt ABS-02: ABBIS product API, context slices, and event connector

**Status: COMPLETED 2026-08-08**
**Depends on:** ABS-00, ABS-01
**Blocks:** ABS-03 through ABS-05

## What was built

- Fixture product API /fixture-product/api/keprix/v1/*
- Context slices, localisation, preview/apply idempotency
- Connector manifest + event ack/outbox


## Goal

Open a manifest-derived, tenant-safe ABBIS service API for Keprix reads and actions.

## Must-haves

1. Common health, capabilities, token exchange, current context and event ack.
2. Context API `/api/keprix/v1/context/{slice_key}` validates actor, tenant,
   stakeholder, accessory entitlement, record scope, purpose and requested fields.
3. Cursor reads for projects, sites, boreholes, drilling reports, rigs, fleet,
   stock, workers, quotes, finance, compliance, marketplace and association views.
4. Action preview/apply pairs for quote, report, inventory, maintenance task,
   activity/message, payment reminder and marketplace operations. Apply requires
   preview hash, idempotency, current versions and approval where configured.
5. Event outbox publishes versioned events from mesh manifests, including job,
   stock, maintenance, quote, payment, compliance, marketplace and channel events.
6. Keprix connector consumes at least once, checkpoints and acknowledges; retries
   cannot duplicate a stock, finance, message or task mutation.
7. Provide `/api/keprix/v1/localisation` and schema/version discovery so sidecar
   never hardcodes English or stale field names.
8. Product-side IsolationEnforcer runs on every endpoint, including health detail,
   batch, export, aggregate, webhook and error paths.
9. Log ids and policy outcomes, not personal, financial, location or raw field data.

## Acceptance

- [x] Manifest events and context slices have contract tests
- [x] Cross-stakeholder, accessory and tenant access fails closed
- [x] Stale preview or duplicate idempotency cannot double-post
- [x] Connector remains schema-version aware
