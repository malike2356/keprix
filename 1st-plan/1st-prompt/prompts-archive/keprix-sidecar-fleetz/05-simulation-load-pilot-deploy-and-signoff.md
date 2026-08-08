# Prompt FZS-05: Fleetz simulation, load, pilot, deploy, and sign-off

**Status: COMPLETED 2026-08-08**


## What was built

- `domain-packs/fleetz/` advisory sidecar (HTTP :3354, `/v1/products/fleetz/*`)
- Architecture, product API, streams/resilience, and pilot sign-off docs
- Deterministic calculators, safety gates, fixture connector, playbooks, simulator
- `keprix product provision|plan|status|rollback fleetz` CLI wiring
- Tests: `pytest domain-packs/fleetz/tests/test_fleetz_sidecar.py` (10 passed)
- Local deploy: `bash domain-packs/fleetz/scripts/deploy-local.sh`

**Depends on:** FZS-00 through FZS-04

## Goal

Prove fleet isolation, evidence quality, event-scale resilience and safety before
a Ghana pilot uses Keprix assistance.

## Must-haves

1. Contract, pack, connector, event, calculation, provisioning, channel,
   retention, isolation and rollback tests.
2. Simulator produces normal trips, refuels, drains, theft-like events, GPS gaps,
   sensor drift, spoofing, duplicate/out-of-order points, geofence and maintenance.
3. Golden cases measure false accusation, missed anomaly, evidence completeness,
   stale-data refusal and deterministic reconciliation.
4. Security cases: cross-fleet ids, forged events/tokens, precise-location export,
   prompt-injected notes, command request, replayed notification and SSRF.
5. Load tests model vehicle counts, event bursts, reconnects, dashboard queries and
   model budgets. Primary Fleetz ingestion latency cannot regress materially.
6. Failure drills cover broker/API/model/sidecar outage, late data, queue full,
   cancellation, notification failure, key rotation and rollback.
7. Pilot starts read-only/advisory with a small owned fleet, known sensor calibration,
   human-reviewed cases, support owner, thresholds and immediate kill switch.
8. Vehicle command capabilities remain NOT READY unless a future independent
   safety programme is explicitly approved.

## Acceptance

- [ ] Primary tracking remains stable under sidecar load/outage
- [ ] Cross-fleet and command attempts fail closed
- [ ] Fuel findings meet pilot evidence/false-positive thresholds
- [ ] Rollback and event reconciliation are demonstrated
