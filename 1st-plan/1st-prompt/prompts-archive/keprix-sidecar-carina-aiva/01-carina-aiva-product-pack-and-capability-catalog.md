# Prompt 517 / CAS-01: Carina/Aiva product pack and capability catalog

**Status: COMPLETED 2026-08-08**
**Series:** 516-531
**Depends on:** 516, KSF-00 (pack registry)
**Blocks:** 518, 523-525
**Writing style:** plain ASCII only.

## Goal

Install a versioned product pack that advertises every Keprix capability Carina
and Aiva may consume, with live/stub/not_configured honesty.

## Must-haves

1. Pack keys: `carina` and `aiva` (shared nodes allowed; Aiva wrappers for personas,
   SKUs, nav copy only).
2. Manifest lists capability nodes with schemas, risk class, Soft Wall rules,
   entitlements, budgets, timeouts, idempotency, and health.
3. Catalog groups at minimum:
   - agent.run / agent.interrupt
   - soft_wall.*
   - crm.* (read, propose, enroll, pipeline, analytics)
   - discovery.* / outreach.*
   - vical.* / booking.*
   - scout.* (hooks only; Scout remains governance console)
   - memory.* / rag.*
   - playbook.* / jobs.*
   - channels.* (Telegram/operator; WA/SMS flagged)
   - data.* (datasets/jobs/export as already in Keprix)
4. Nodes that need owner credentials return `not_configured` without pretending live.
5. Feature inventory + self-knowledge snippets for operators.
6. Tests: pack validate/install; disable removes invoke; Aiva wrapper does not
   duplicate carina node implementations.

## Acceptance

- [ ] `/capabilities` (or pack inspect) lists P0-P2 nodes with status
- [ ] Cross-product composition with Clinicom/Petraclus fails closed
- [ ] Kill switch disables pack invoke immediately

## Done When

518 can mount northbound routes against a real catalog.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
