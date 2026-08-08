# Prompt 522 / CAS-06: Default engine cutover, circuit breaker, and fallback

**Status: COMPLETED 2026-08-08**
**Series:** 516-531
**Depends on:** 521
**Blocks:** 523-531 (live default)
**Writing style:** plain ASCII only.

## Goal

Make Keprix the default agent engine for opted Carina/Aiva workspaces, with
instant fallback that cannot duplicate side effects.

## Must-haves

1. Per-workspace engine assignment already in OPS becomes authoritative for chat
   invoke routing (not health-only).
2. Cutover checklist: shadow score thresholds, error budget, Soft Wall queue depth,
   owner approval.
3. Circuit breaker: Keprix timeout/5xx/policy storm -> Carina engine fallback.
4. Idempotency: in-flight mutate tools use keys so fallback cannot double-send.
5. Kill switch: force all workspaces to Carina engine without deploy.
6. User-visible degraded banner only when fallback engaged (honest).
7. Rollback runbook + automated switch tests.
8. Update OPS UI copy so "on Keprix" means live chat path.

## Acceptance

- [ ] Opted workspace chat runs via Keprix primary
- [ ] Forced Keprix outage falls back without duplicate outbound
- [ ] Kill switch returns workspaces to Carina within one request cycle

## Done When

Capability nodes (523+) can safely attach to the live engine path.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
