# Observability

## Metrics

`GET /sidecar/v1/projects/{project_key}/metrics` returns product-scoped
operational metrics (request counts, latency, job depth, denials, budget use).

## Audit

Immutable audit records cover pairing, token exchange, invoke, connector calls,
approvals, job lifecycle, event delivery, kill-switch changes, and retention.

## Correlation

Every request should carry a correlation id and optional trace parent. Sidecar
propagates correlation into connector calls and outbound events.

## Logging rules

Log ids, classifications, and outcome codes. Do not log raw secrets, full
prompts with regulated content, or live credentials.

## Health

- Liveness: process up
- Readiness: dependencies healthy and not draining
- Degraded: advertise via health payload when a dependency is stubbed
