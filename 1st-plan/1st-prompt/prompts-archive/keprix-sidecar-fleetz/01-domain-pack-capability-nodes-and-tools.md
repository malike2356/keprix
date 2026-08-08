# Prompt FZS-01: Fleetz pack, capability nodes, and tools

**Status: COMPLETED 2026-08-08**


## What was built

- `domain-packs/fleetz/` advisory sidecar (HTTP :3354, `/v1/products/fleetz/*`)
- Architecture, product API, streams/resilience, and pilot sign-off docs
- Deterministic calculators, safety gates, fixture connector, playbooks, simulator
- `keprix product provision|plan|status|rollback fleetz` CLI wiring
- Tests: `pytest domain-packs/fleetz/tests/test_fleetz_sidecar.py` (10 passed)
- Local deploy: `bash domain-packs/fleetz/scripts/deploy-local.sh`

**Depends on:** FZS-00
**Blocks:** FZS-02, FZS-04

## Goal

Build `domain-packs/fleetz/` with grounded fleet, fuel, maintenance and operations
capabilities that cite Fleetz telemetry and event ids.

## Must-haves

1. Manifest, schemas, units, glossary, policies, tools, playbooks, event types,
   model routes and deterministic fixtures.
2. Read nodes: fleet/vehicle/driver/trip/geofence/alert/maintenance get/search,
   position summary, fuel series summary, device/sensor health and audit.
3. Analysis nodes: `fleet_brief`, `fuel_anomaly_explain`, `theft_case_assess`,
   `route_deviation_explain`, `idle_waste_summary`, `driver_risk_summary`,
   `maintenance_forecast`, `sensor_quality_assess`, `trip_report`, `ask_fleet`.
4. Proposal nodes: `alert_rule_propose`, `maintenance_task_propose`,
   `driver_message_draft`, `incident_case_propose`, `geofence_change_propose`,
   `route_plan_propose`, `fuel_reconciliation_propose`.
5. Product action nodes initially limited to approved notification, task/case
   creation and report export. Vehicle/device commands advertise disabled.
6. Deterministic services calculate distance, fuel delta, idle duration, geofence,
   rates and thresholds. LLM explains but cannot fabricate points or recalculate
   from sampled prose.
7. Every result carries fleet/vehicle/event ids, source window, freshness, sensor
   quality, units, confidence and observed/derived/inferred labels.
8. Location and driver data is minimised by role and purpose. Aggregate summaries
   enforce safe fleet scope and do not reveal off-duty tracking.

## Acceptance

- [ ] Nodes reject stale/insufficient series for definitive conclusions
- [ ] Calculations reconcile to deterministic Fleetz services
- [ ] Command nodes are absent or disabled by default
- [ ] Every result is fleet-scoped and evidence-linked
