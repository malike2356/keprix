# Prompt 519 / CAS-03: Southbound Carina/Aiva product API connector

**Status: COMPLETED 2026-08-08**
**Series:** 516-531
**Depends on:** 518
**Blocks:** 520, 523-527
**Writing style:** plain ASCII only.

## Goal

Give Keprix an allowlisted, authenticated connector into Carina/Aiva product APIs
so capabilities can read/propose/mutate through the product SoT.

## Must-haves

1. Product endpoints (minimum):
   - `GET /api/keprix/v1/health`
   - `GET /api/keprix/v1/capabilities`
   - `POST /api/keprix/v1/token/exchange`
   - `GET /api/keprix/v1/context`
   - `POST /api/keprix/v1/events/ack`
2. Declared read slices: workspace summary, user/actor, entitlements, Soft Wall
   pending counts, CRM record by id (projected), booking refs, approval item by id.
3. Declared actions: create Soft Wall approval request ack, attach artifact ref,
   schedule/job ack, idempotent CRM propose apply only with approval evidence.
4. Manifest documents every route: method, path, purpose, sensitivity, grant,
   rate limit, idempotency, approval rule, response schema.
5. Default deny for undeclared routes. No UI scraping. No direct SQL.
6. Field projection + pagination; never dump whole tenant CRM by default.
7. Tests: allowlist pass; denied route; projection strips sensitive fields.

## Acceptance

- [ ] Connector cannot call undeclared internal admin routes
- [ ] Context slice is purpose-limited
- [ ] Idempotent action replay does not double-write

## Done When

520 can issue short-lived tokens against this connector.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
