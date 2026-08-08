# Prompt 518 / CAS-02: Northbound sidecar routes and legacy bridge compatibility

**Status: COMPLETED 2026-08-08**
**Series:** 516-531
**Depends on:** 517, KSF-01
**Blocks:** 519-522
**Writing style:** plain ASCII only.

## Goal

Expose the product-sidecar northbound HTTP API for Carina/Aiva while keeping
`POST /carina/agent/run` working as a compatibility shim.

## Must-haves

1. Mount under `/v1/products/{carina|aiva}` (or equivalent foundation path):
   health, capabilities, manifest, sessions, invoke, jobs, events, approvals
   decision, metrics.
2. Map legacy `/carina/agent/run` to `agent.run` node without breaking existing
   shared-token clients.
3. `/invoke` validates node key, grant, tenant, schema, policy, budget, Soft Wall.
4. No generic "run any Keprix tool by name" escape hatch outside the catalog.
5. Correlation id required end-to-end; structured errors (`not_configured`,
   `denied`, `soft_wall_required`, `budget_exceeded`).
6. Contract tests for both legacy and v1 routes.
7. Docs: operator + engineer migration from bridge-only to capabilities API.

## Acceptance

- [ ] Existing KeprixBridgeService still succeeds against legacy route
- [ ] New client can list capabilities and invoke a read-only node
- [ ] Unknown node and cross-tenant invoke fail closed

## Done When

519 can call southbound using the same request context model.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
