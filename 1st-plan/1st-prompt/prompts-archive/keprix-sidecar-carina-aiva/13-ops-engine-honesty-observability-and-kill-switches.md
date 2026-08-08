# Prompt 529 / CAS-13: OPS engine honesty, observability, and kill switches

**Status: COMPLETED 2026-08-08**
**Series:** 516-531
**Depends on:** 522
**Blocks:** 531
**Writing style:** plain ASCII only.

## Goal

Make Carina OPS agent-engine controls tell the truth about Keprix consumption and
provide kill switches, logs, and budgets operators can trust.

## Must-haves

1. Health shows: sidecar reachable, pack version, capability counts by status,
   shadow/primary mode, open Soft Wall count, circuit state.
2. "Workspace on Keprix" requires successful primary invoke path probe, not only
   `/api/health`.
3. Logs: correlation id, node key, deny reason, latency, cost; redaction enforced.
4. Kill switches: global engine force-carina, pack disable, node disable, provider
   disable, outbound kill.
5. Budgets per workspace/node with Soft Wall raise.
6. Do not merge Clinicom/Scout OPS into this panel.
7. Contabo deploy notes: verify carinaai.uk 200 if Contabo touched.
8. Tests: probe fails => workspace not marked healthy-on-keprix; kill switch effect.

## Acceptance

- [ ] OPS UI cannot claim full Keprix while only legacy bridge health passes
- [ ] Kill switches covered by automated tests
- [ ] Metrics exportable without secrets

## Done When

Operators can run and stop the Keprix brain safely from OPS.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
