# Propreneur sidecar observability runbook

**Audience:** support and on-call
**Contract version:** 1.0.0

## What to log

Structured fields only:

- correlation ID
- tenant or workspace pseudonym / internal ID
- actor ID
- engine / product (`propreneur`)
- tool or node name
- risk class
- approval ID (when soft-wall)
- status / error code
- duration_ms

Never log credentials, full property addresses with PII dumps, unrestricted
record bodies, or raw model prompts that contain tenant secrets.

## Metrics to watch

| Metric | Alert idea |
| --- | --- |
| Request volume and success rate | error rate above soak baseline |
| Latency p50 / p95 | p95 above SLO |
| Authorization denials | spike may indicate mis-scoped grants |
| Soft-wall approval outcomes | unexpected deny or stale approvals |
| Circuit open | Keprix or Propreneur transport failure |
| Idempotent replays | healthy retries vs duplicate client bugs |
| Contract mismatches | block deploy |

## Traces

Propagate the same correlation ID across Propreneur HTTP, Keprix invoke, and
tool callbacks. Prefer one trace tree per user-visible action.

## SLOs (starting template)

- Availability of `/v1/products/propreneur/health`: 99.5% monthly
- Invoke p95 for read nodes: under 2s local; under 3s Contabo loopback
- Auth failure rate: investigate if sustained above 1% of authentications
- Ambiguous mutations: create reconciliation case; never auto-retry another engine

## User-visible error to safe diagnosis

| User sees | Likely cause | Operator check |
| --- | --- | --- |
| Action not available | pack disabled or node soft-walled | `registry.health('propreneur')`, feature flag |
| Permission denied | missing scope or cross-tenant | grants, actor/tenant mapping, audit |
| Try again later | circuit open / timeout | Propreneur health, loopback `13333`, connector allowlist |
| Waiting for approval | soft_wall mutate/propose/destructive | approvals UI, expiry, material args unchanged |
| Already done | idempotent replay | execution ledger by idempotency key |

## Failure drills

Run periodically:

1. Keprix unavailable: Propreneur must fail closed or use native fallback only
   before side effects begin.
2. Propreneur unavailable: Keprix circuit opens; no silent mutate retry.
3. Slow responses and cancellation: bounded iterations, no infinite tool loop.
4. Malformed model output: validation error envelope; no mass assignment.

## Dashboards

Link product dashboards here when created. Until then use:

```bash
curl -fsS http://127.0.0.1:13333/v1/products/propreneur/health
curl -fsS http://127.0.0.1:13333/v1/products/propreneur/metrics
```

On Contabo, after any deploy also verify `https://carinaai.uk/` returns HTTP 200.
