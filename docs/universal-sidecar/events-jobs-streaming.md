# Events, jobs, and streaming

## Events

CloudEvents-style envelopes with stable id, type, version, source, subject,
tenant, occurred time, correlation, trace, schema, and sensitivity.

- Delivery is at least once; consumers dedupe by product/deployment/event id.
- Ingest: `POST /sidecar/v1/projects/{project_key}/events`
- Stream: `GET /sidecar/v1/projects/{project_key}/events/stream` (SSE)
- Webhooks are signed (HMAC-SHA256 or Ed25519) with timestamp tolerance and
  replay protection.

## Jobs

Async capabilities persist state, checkpoint, attempts, next retry, budget,
progress, result references, and dead-letter reason.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/jobs` | Start async capability |
| GET | `/jobs/{job_id}` | Status / progress / result refs |
| POST | `/jobs/{job_id}/cancel` | Idempotent cancel |

External side effects use a transactional outbox and idempotency key. Retries
must not duplicate notifications or writes.

## Reliability controls

Circuit breakers, bounded exponential backoff, dependency timeouts, queue
limits, load shedding, cancellation, and per-project kill switches are
mandatory. Product core remains usable during Keprix outage.
