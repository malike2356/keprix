# Keprix sidecar readiness for Fleetz

**Status: COMPLETED 2026-08-08**


## What was built

- `domain-packs/fleetz/` advisory sidecar (HTTP :3354, `/v1/products/fleetz/*`)
- Architecture, product API, streams/resilience, and pilot sign-off docs
- Deterministic calculators, safety gates, fixture connector, playbooks, simulator
- `keprix product provision|plan|status|rollback fleetz` CLI wiring
- Tests: `pytest domain-packs/fleetz/tests/test_fleetz_sidecar.py` (10 passed)
- Local deploy: `bash domain-packs/fleetz/scripts/deploy-local.sh`

**Product:** African fleet tracking and fuel intelligence platform
**Contract:** `../ref-keprix-product-sidecar-contract.md`

## Build order

1. `00-architecture-safety-telemetry-and-control-boundary.md`
2. `01-domain-pack-capability-nodes-and-tools.md`
3. `02-product-api-connector-telemetry-read-and-actions.md`
4. `03-provisioning-streams-geospatial-resilience-and-edge.md`
5. `04-alert-investigation-maintenance-and-operator-workflows.md`
6. `05-simulation-load-pilot-deploy-and-signoff.md`

Keprix is advisory by default. It cannot issue arbitrary vehicle, immobilisation,
tracker, fuel, or driver commands. Safety-critical actions remain product-owned,
strongly authenticated, policy-gated and human-confirmed.
