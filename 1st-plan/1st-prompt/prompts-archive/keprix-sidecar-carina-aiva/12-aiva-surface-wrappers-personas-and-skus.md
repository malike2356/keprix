# Prompt 528 / CAS-12: Aiva surface wrappers, personas, and SKUs

**Status: COMPLETED 2026-08-08**
**Series:** 516-531
**Depends on:** 517, 522
**Blocks:** 531
**Writing style:** plain ASCII only.

## Goal

Keep Aiva as a commercial surface on the same Keprix-backed runtime: branding,
routes, personas, and SKUs differ; engine and nodes stay shared.

## Must-haves

1. Follow `CARINA-AIVA-SOFT-SEPARATION.md`.
2. Aiva pack wrapper references shared `carina` nodes; adds Aiva persona packs,
   onboarding copy, and entitlement map only.
3. Do not fork agent loop, Soft Wall, CRM domain, or sidecar HTTP for Aiva.
4. hireaiva UI keeps calling product APIs; those APIs call sidecar.
5. Stripe: map existing Aiva price IDs from `.access` SoT to grants; never create
   prices.
6. Tests: Aiva entitlement matrix; shared node code path identical for carina/aiva
   product keys except wrapper metadata.

## Acceptance

- [ ] No second Python/TS agent runtime for Aiva
- [ ] Aiva SKU gates worker nodes without hiding platform admin nodes incorrectly
- [ ] Soft separation checklist signed in docs

## Done When

Aiva consumes Keprix through the same brain with product-local packaging only.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
