# Fleetz southbound product API (for future Fleetz Node service)

Keprix calls only declared routes. Default deny for everything else.
No SQL credentials. No Traccar command APIs. No UI scrape.

## Required endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/keprix/v1/health` | Product liveness |
| GET | `/api/keprix/v1/capabilities` | Grants and entitlement negotiation |
| POST | `/api/keprix/v1/token/exchange` | Short-lived workload token |
| GET | `/api/keprix/v1/context` | Purpose-limited context slice |
| POST | `/api/keprix/v1/events/ack` | Event acknowledgement |
| GET | `/api/keprix/v1/fleets` / `{id}` | Fleet projected reads |
| GET | `/api/keprix/v1/vehicles` / `{id}` | Vehicle projected reads |
| GET | `/api/keprix/v1/drivers` / `{id}` | Role-minimised driver reads |
| GET | `/api/keprix/v1/trips` / `{id}` | Trip summaries |
| GET | `/api/keprix/v1/vehicles/{id}/positions/summary` | Downsampled positions |
| GET | `/api/keprix/v1/vehicles/{id}/fuel/summary` | Downsampled fuel series |
| GET | `/api/keprix/v1/geofences` / alerts / maintenance / audit | Bounded reads |
| POST | `/api/keprix/v1/actions/*/preview` | Preview notification/task/case/rule |
| POST | `/api/keprix/v1/actions/*/apply` or create | Idempotent apply with approval |

## Query rules

- Require fleet scope (from token) and vehicle ids where relevant
- Bounded time range, resolution/aggregation, field projection, cursor, max points
- Missing samples stay unknown; never coerce to zero
- Cross-fleet ids return empty/denied

## Writes

- Idempotency key required
- Current object version when updating
- Approval evidence for apply
- Duplicate webhook cannot duplicate SMS/push/task/case

## Logging

Never log precise routes, driver identity, raw telemetry, or service tokens.
