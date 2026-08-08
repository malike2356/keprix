# Prompt KUS-06: Events, durable jobs, webhooks, streaming, and idempotency

**Status: COMPLETED 2026-08-08**
**Depends on:** KUS-02 through KUS-05
**Blocks:** KUS-08 through KUS-12

## What was built

- CloudEvents inbox/outbox, job states, Idempotency-Key, cancel quarantine
- Webhook delivery log + signed digests; per-project fairness

## Goal

Support reliable asynchronous integration for long-running agent work and
at-least-once project events without duplicate external effects.

## Must-haves

1. CloudEvents-compatible envelope with id, source, type, spec/schema version,
   project/deployment/environment, tenant, subject, occurred/received times,
   correlation/trace, sensitivity and payload.
2. Signed inbound webhook/event with timestamp tolerance, body digest, key id,
   replay cache, schema, request limit and dead-letter for valid but unprocessable.
3. Durable inbox/outbox dedupes by project/deployment/event id and preserves
   ordering key when configured. Delivery receipts and acknowledgement are typed.
4. Job state: queued, running, waiting, awaiting_approval, paused, succeeded,
   partially_succeeded, failed, cancelled, expired, dead_letter. Persist checkpoint,
   attempts, progress, budget, next retry, results and errors.
5. `Idempotency-Key` required for job creation and all side-effecting callbacks.
   Same key/input returns prior result; same key/different input is conflict.
6. SSE is canonical progress transport with event id/cursor, heartbeat, reconnect,
   retention window and snapshot fallback. Optional WebSocket maps same events.
7. Outbound webhooks use allowlisted HTTPS destinations, signing, delivery log,
   exponential backoff/jitter, max attempts, disable-on-gone and manual replay.
8. Cancellation is cooperative and visible; late provider results are quarantined
   and cannot trigger actions after cancellation or approval expiry.
9. Per-project queues, fairness, concurrency, priority ceilings, TTL, load shedding,
   circuit breakers and kill switches prevent noisy-neighbour starvation.
10. Project outage queues bounded callbacks and never blocks core Keprix shutdown.

## Acceptance

- [x] Duplicate event/job/webhook cannot duplicate a side effect
- [x] Restart resumes jobs and event cursor consistently
- [x] Cancellation prevents late action
- [x] Noisy project cannot starve another project
