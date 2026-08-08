# Fleetz Keprix sidecar architecture and vehicle-control boundary

**Status:** BINDING FOR FLEETZ SIDECAR  
**Date:** 2026-08-08  
**Product:** African fleet tracking and fuel intelligence (Ghana-first)

## Ownership

| Concern | Owner |
| --- | --- |
| User/device auth, tenancy, entitlements, billing | Fleetz |
| Telemetry ingest (TCP/UDP/MQTT), Traccar gateway, TimescaleDB/PostGIS | Fleetz |
| Primary alert/geofence/fuel rules and map UI | Fleetz |
| Vehicle/device commands (immobilise, fuel cut, tracker config, firmware) | Fleetz only |
| Explanation, correlation, prediction, drafts, operator playbooks | Keprix sidecar |
| Agent memory, jobs, approvals assist, audit of sidecar actions | Keprix |

Keprix never receives unrestricted database access, never scrapes Fleetz UI routes,
and never holds Traccar or tracker command credentials.

## Device-to-dashboard and sidecar paths

```text
Tracker/sensor --> Traccar / Go ingest --> Fleetz Node API --> TimescaleDB/PostGIS
                                              |                    |
                                              | WebSocket/maps     | primary alerts
                                              v                    v
                                         Fleetz web/mobile     SMS/push rules
                                              |
                                              | southbound /api/keprix/v1/*
                                              | (projected, bounded, signed)
                                              v
                                         Keprix Fleetz sidecar
                                         (observe / recommend / notify drafts)
                                              |
                                              | preview/apply (idempotent)
                                              v
                                         Fleetz product apply
                                         (human approval for writes)
```

Observation path: Fleetz emits derived events (not raw GPS points) to the sidecar.  
Recommendation path: sidecar analysis nodes cite fleet/vehicle/event ids and quality.  
Notification path: approved notification/task/case/report only.  
Control path: disabled in default pack; product-owned two-person approval if ever enabled.

## Separation of planes

1. **Observation** - read projected fleet/vehicle/trip/fuel/alert summaries.
2. **Recommendation** - analysis and proposal nodes; never mutate devices.
3. **Notification** - draft SMS/push/Telegram/operator messages; apply only after product approval.
4. **Control** - immobilise, restart/cut fuel, tracker config, firmware, live geofence mutate,
   driver emergency instruction. Default grant: none. Sidecar must not connect to tracker
   TCP/UDP, MQTT command topics, or Traccar command APIs.

## Safety-critical actions (default deny)

- Immobilise / engine stop / fuel cut
- Tracker config or firmware update
- Live geofence create/update/delete apply
- Driver emergency instruction that implies stop/divert
- Bulk export of precise routes or off-duty driver tracking

Any future enablement requires product-owned step-up or two-person approval, device
capability validation, and an independent safety programme sign-off (see pilot docs).

## Threat model (summary)

| Threat | Mitigation |
| --- | --- |
| False fuel theft accusation | Evidence vs hypothesis labels; sensor quality gate; no accusation language |
| Stale GPS / missing series | Freshness contract; refuse definitive conclusions |
| Sensor calibration drift | Quality assess node; mark derived not observed |
| Spoofing / forged events | Signed product tokens; schema + sequence validation |
| Account takeover | Short-lived exchanged tokens; least privilege grants |
| Driver surveillance / location leakage | Role-purpose minimisation; aggregate fleet summaries |
| Unsafe command | Command nodes disabled; no device credentials |
| Prompt-injected notes | Treat notes as untrusted data; never execute instructions |
| Cross-fleet tracking | Hard fleet/tenant scope on every read/write |
| Alert storms | Coalesce by fleet/vehicle/window; model budget caps |

## Telemetry quality contract

- Event-time is authoritative; processing-time is secondary.
- Out-of-order and late events are accepted with sequence checks; never invent zeros for gaps.
- Units: preserve original sensor units; Ghana default timezone `Africa/Accra`, currency GHS.
- Map precision: summaries downsampled product-side; precise routes require narrow purpose.
- Retention/deletion events from Fleetz purge sidecar caches, jobs, and memory namespaces.
- Stale or low-quality series are labelled `non_actionable` and cannot drive definitive claims.

## Ghana connectivity and edge/degraded mode

- Device ingestion stays in Fleetz during sidecar or network outage.
- Sidecar consumes delayed summaries and labels latency; it cannot emit retroactive "live" alerts.
- Missing data is unknown, never zero fuel or zero distance.
- Queued analyses recheck freshness on dequeue; expired windows are refused.

## Credentials

| Credential | Present on sidecar? |
| --- | --- |
| Fleetz product API workload token (exchanged, short-lived) | Yes (vault) |
| Traccar admin / command API | No |
| MQTT command topic publish | No |
| Tracker TCP/UDP direct | No |
| Direct TimescaleDB SQL | No |
