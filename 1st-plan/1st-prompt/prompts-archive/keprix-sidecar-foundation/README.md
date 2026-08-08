# Keprix multi-product sidecar foundation

**Status: COMPLETED 2026-08-08**
**Contract:** `../ref-keprix-product-sidecar-contract.md`

Build once before product packs depend on it:

1. `00-product-pack-registry-and-runtime-boundary.md`
2. `01-northbound-http-capability-and-node-api.md`
3. `02-southbound-connectors-identity-and-grants.md`
4. `03-provisioning-events-jobs-resilience-and-operations.md`
5. `04-security-isolation-contract-tests-and-release.md`

This is platform plumbing only. Product-specific schemas, data, personas, tools,
policy and deployment decisions remain in the separate product queues
(including `keprix-sidecar-carina-aiva/` for Carina/Aiva full-capability consumption).

## What was built

- Shared product sidecar foundation under `src/keprix/product_sidecar/`
- Fixture packs + registry install/validate/upgrade/rollback/kill
- Northbound `/v1/products/{product_key}` including events/stream and durable jobs
- Southbound ProductConnector with SSRF/default-deny and FakeProductConnector
- CLI: `keprix product provision|plan|status|upgrade|rollback|disable|remove|conformance`
- Conformance gate + release runbook `docs/architecture/product-sidecar-foundation-release.md`
- Tests: `tests/product_sidecar/test_sidecar_foundation.py` (plus existing Carina/Aiva suite)
