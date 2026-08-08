# Prompt FZS-02: Fleetz service API, telemetry read, and safe actions

**Status: COMPLETED 2026-08-08**


## What was built

- `domain-packs/fleetz/` advisory sidecar (HTTP :3354, `/v1/products/fleetz/*`)
- Architecture, product API, streams/resilience, and pilot sign-off docs
- Deterministic calculators, safety gates, fixture connector, playbooks, simulator
- `keprix product provision|plan|status|rollback fleetz` CLI wiring
- Tests: `pytest domain-packs/fleetz/tests/test_fleetz_sidecar.py` (10 passed)
- Local deploy: `bash domain-packs/fleetz/scripts/deploy-local.sh`

**Depends on:** FZS-00, FZS-01
**Blocks:** FZS-03 through FZS-05

## Goal

Open bounded Fleetz endpoints for Keprix without bulk database or live command access.

## Must-haves

1. Common health, capabilities, token exchange, context and event ack.
2. Reads for fleets, vehicles, drivers by authorised role, trips, positions summary,
   fuel summary/downsampled series, geofences, alerts, maintenance, cases, device
   health and aggregates. Raw high-frequency data needs narrow purpose and limits.
3. Query parameters require vehicle ids, bounded time range, resolution/aggregation,
   field projection, cursor and maximum points. Product enforces tenant scope.
4. Preview/apply for notification, maintenance task, incident case, alert rule and
   report. Geofence proposal is preview-only initially. No immobilise/device config.
5. Product event outbox sends telemetry-derived events rather than every raw point:
   vehicle state, trip, fuel anomaly, geofence, sensor health, maintenance and alert.
6. Connector validates event time, units, coordinates, freshness, sequence and
   schema. It handles late/out-of-order events and never treats missing data as zero.
7. Write actions require idempotency, current object version, approval evidence,
   role and product policy. Duplicate webhook cannot duplicate SMS/push/task/case.
8. Never log precise routes, driver identity, raw telemetry or service tokens.

## Acceptance

- [ ] Queries are bounded and downsampled product-side
- [ ] Cross-fleet ids return no data
- [ ] Missing/stale telemetry remains unknown
- [ ] No API route exposes arbitrary tracker command execution
