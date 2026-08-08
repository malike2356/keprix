# Fleetz streams, geospatial, and resilience

## Event consumption

- Broker identity is consume-only on allowlisted derived topics
- Denied: device command, MQTT command, Traccar command, all-tenant wildcards
- Coalesce by fleet/vehicle/window (`calculators.formulas.coalesce_event_batch`)
- Prioritise safety/high priority alerts within batches
- One model call per batch window, never per raw GPS point

## Geospatial and units

- Location computation for apply remains Fleetz/PostGIS
- Sidecar may use haversine helpers for advisory distance only
- Preserve original sensor units; Ghana defaults Africa/Accra + GHS for display

## Sidecar outage

- Fleetz ingest, storage, maps, and primary alerts continue
- Eligible analyses queue with TTL; dequeue rechecks freshness
- Edge/poor-network: delayed summaries labelled; no retroactive live alerts

## Limits

- Per-fleet quotas and model cost caps in provision plan
- Kill switches: product, fleet, node, provider
- Upgrade/rollback drains consumers, checkpoints offsets, suppresses replayed notifications
