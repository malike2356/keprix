# Prompt 527 / CAS-11: Memory authority, events, retention, and no dual-write

**Status: COMPLETED 2026-08-08**
**Series:** 516-531
**Depends on:** 521, 524
**Blocks:** 531
**Writing style:** plain ASCII only.

## Goal

Define durable memory and event authority so Carina/Aiva + Keprix do not fork
truth or leak retention.

## Must-haves

1. Authority table:
   - Wave 1 (shadow): Carina session memory SoT; Keprix ephemeral traces only
   - Wave 2 (Keprix primary chat): Keprix session memory SoT for agent turns;
     Carina history read-only import/bridge as needed
   - Product CRM/records: always product/Keprix CRM store via capabilities, not
     duplicated TS stores
2. Event envelope for product <-> sidecar (CloudEvents-style) with dedupe.
3. Deletion/DSAR/retention from product propagates to Keprix indexes/caches/jobs.
4. Ban dual-write of the same memory document to Carina SQLite/TS and Keprix
   without explicit migration job.
5. Provenance on generated facts.
6. Tests: retention delete removes Keprix workspace memory; duplicate event id
   is noop; shadow mode writes no durable customer memory in Keprix.

## Acceptance

- [ ] Documented authority table checked into docs/architecture
- [ ] DSAR delete proof for one workspace
- [ ] No silent dual-write in default configs

## Done When

Cutover cannot create split-brain memory.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
