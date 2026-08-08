# Prompt FZS-00: Fleetz sidecar architecture and vehicle-control boundary

**Status: COMPLETED 2026-08-08**


## What was built

- `domain-packs/fleetz/` advisory sidecar (HTTP :3354, `/v1/products/fleetz/*`)
- Architecture, product API, streams/resilience, and pilot sign-off docs
- Deterministic calculators, safety gates, fixture connector, playbooks, simulator
- `keprix product provision|plan|status|rollback fleetz` CLI wiring
- Tests: `pytest domain-packs/fleetz/tests/test_fleetz_sidecar.py` (10 passed)
- Local deploy: `bash domain-packs/fleetz/scripts/deploy-local.sh`

**Depends on:** Fleetz tech stack, shared contract
**Blocks:** FZS-01 through FZS-05

## Goal

Define Keprix as fleet intelligence and operator assistance beside Traccar,
TimescaleDB/PostGIS, Node API and real-time services, never the telemetry source
of truth or an unbounded vehicle command plane.

## Must-haves

1. Inventory fleets/tenants, users/roles, vehicles, devices, drivers, trips,
   positions, fuel, sensors, geofences, alerts, maintenance, incidents, commands,
   billing, SMS/push, web/mobile and planned deployment.
2. Ownership: Fleetz authenticates users/devices, stores telemetry, detects primary
   events, executes commands and owns UI; Keprix explains, correlates, predicts,
   drafts actions and runs approved operator playbooks.
3. Separate observation, recommendation, notification and control. Keprix cannot
   connect directly to tracker TCP/UDP, MQTT command topics or Traccar command APIs.
4. Define safety-critical actions: immobilise, restart/cut fuel, tracker config,
   firmware, geofence change, driver instruction and emergency escalation. Default
   sidecar has no grant; any future action requires product-owned two-person or
   strong step-up approval and device capability validation.
5. Threat-model false fuel theft, stale GPS, sensor calibration drift, spoofing,
   account takeover, driver surveillance, unsafe command, prompt-injected notes,
   cross-fleet tracking, location leakage and alert storms.
6. Define telemetry freshness/quality, event-time, out-of-order, dedupe, units,
   timezone, map precision, retention and privacy contracts.
7. Define Ghana connectivity and edge/degraded behaviour with no unsafe inference
   from missing data.

## Acceptance

- [ ] Diagram covers device-to-dashboard and sidecar paths
- [ ] Keprix has no direct vehicle/device command credential
- [ ] Stale or low-quality telemetry is visibly non-actionable
- [ ] Cross-fleet location isolation is explicit
