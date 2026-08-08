# Prompt FZS-03: Fleetz provisioning, streams, geospatial resilience, and edge

**Status: COMPLETED 2026-08-08**


## What was built

- `domain-packs/fleetz/` advisory sidecar (HTTP :3354, `/v1/products/fleetz/*`)
- Architecture, product API, streams/resilience, and pilot sign-off docs
- Deterministic calculators, safety gates, fixture connector, playbooks, simulator
- `keprix product provision|plan|status|rollback fleetz` CLI wiring
- Tests: `pytest domain-packs/fleetz/tests/test_fleetz_sidecar.py` (10 passed)
- Local deploy: `bash domain-packs/fleetz/scripts/deploy-local.sh`

**Depends on:** FZS-02
**Blocks:** FZS-05

## Goal

Provision Keprix alongside Fleetz with bounded event consumption, regional
resilience and explicit behaviour during connectivity or data-quality failures.

## Must-haves

1. `keprix product provision fleetz` registers pack, workload identity, callbacks,
   event topics, tenant namespace, policies, budgets, geospatial/time-series helper
   endpoints, notification grants and an idempotent receipt.
2. Consume derived events through a dedicated broker identity and topic allowlist.
   Keprix never subscribes to command topics or all-tenant wildcards.
3. Backpressure and coalescing prevent telemetry storms from creating one model
   call per point. Batch by fleet/vehicle/window and prioritise safety alerts.
4. Configure Ghana timezone/currency/units and preserve original sensor units.
   Location computation uses PostGIS/Fleetz, not model math.
5. Sidecar outage does not interrupt ingestion, storage, maps, primary alerts or
   product rules. Eligible analyses queue with TTL and freshness recheck.
6. Edge/poor-network mode retains device ingestion in Fleetz. Keprix consumes
   delayed summaries and labels latency; it cannot issue retroactive alerts as live.
7. Resource limits, per-fleet quotas, model cost caps, retention, deletion,
   encryption, backup, key rotation and kill switches.
8. Upgrade/rollback drains consumers, checkpoints offsets and avoids replayed
   notifications or missed primary product alerts.

## Acceptance

- [ ] Event storm stays within queue/model budgets
- [ ] Sidecar stop has no effect on core tracking and alerts
- [ ] Replay rechecks freshness and deduplicates actions
- [ ] Broker identity cannot publish device commands
