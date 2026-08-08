# Prompt 523 / CAS-07: Expose CRM, outreach, and Soft Wall capabilities

**Status: COMPLETED 2026-08-08**
**Series:** 516-531
**Depends on:** 517, 522 (or 521 for read-only shadow)
**Blocks:** 526
**Writing style:** plain ASCII only.

## Goal

Publish Keprix CRM / discovery / outreach / Soft Wall as sidecar capability nodes
that Carina/Aiva can invoke without reimplementing CRM inside TypeScript.

## Must-haves

1. Nodes for: crm.search, crm.get, crm.ask, list enroll Soft Wall, pipeline board
   read, stage transition Soft Wall, discovery.run (job), outbox retry Soft Wall,
   suppress, contactability check, analytics funnel read.
2. Every mutate/outbound node requires Soft Wall evidence or returns
   `soft_wall_required` with deep link into Carina/Aiva Soft Wall UI.
3. Reuse Keprix CRM package; do not fork domain model.
4. Southbound still authoritative for product entitlements and operator identity.
5. Aiva branding wrappers may rename labels; node keys stay stable.
6. GUI: Carina/Aiva operator surfaces link to Keprix deep links OR embed via
   product routes that proxy status (no iframe secret leak). Prefer product routes.
7. Tests: enroll blocked without Soft Wall; cross-workspace CRM deny; not_configured
   for owner-gated Nice channels remains honest.

## Acceptance

- [ ] Carina client can Soft Wall-enroll a list via invoke + approval decision
- [ ] Pipeline read matches Keprix board for same workspace
- [ ] No second CRM database appears in Carina

## Done When

Carina/Aiva can operate Must CRM through Keprix capabilities.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
