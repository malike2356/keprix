# Prompt KUS-09: Universal sidecar operator UI and observability

**Status: COMPLETED 2026-08-08**
**Depends on:** KUS-01 through KUS-07
**Blocks:** KUS-12

## What was built

- `/settings/sidecars` operator page + nav entry
- Budgets/kill switches in registry; metrics endpoint

## Goal

Give self-hosters a visual place to configure and supervise projects without
editing hidden JSON or relying on server logs.

## Must-haves

1. Admin routes under `/settings/sidecars` or correct existing integration group:
   projects, pairing, capabilities, connectors, events, jobs, approvals, memory,
   budgets, health, audit and configuration diff.
2. Project overview shows deployment/environment, contract/config/pack versions,
   connection, last health, active grants, requested/denied capabilities, queues,
   recent runs, errors, spend and kill-switch state.
3. Manifest editor is schema-driven with raw YAML option, validation, redacted
   secret references, risk diff, plan/apply and rollback. Never display secret value.
4. Connector tester invokes only declared test/read operation with preview and
   redacted response. No arbitrary URL/method console.
5. Capability graph lists node risk, grants, approvals, dependencies, status,
   schemas and recent use. UI can disable but cannot create unavailable nodes.
6. Jobs/events views show progress, attempts, cursor, dedupe, callback deliveries,
   dead letters, retry/cancel and correlation. Actions are permission/audit gated.
7. Approval inbox shows exact action/input hashes, project actor/purpose, expiry,
   side effects and material-change invalidation.
8. Budgets and limits by project/tenant/node/provider for requests, tokens, cost,
   jobs, concurrency, queue, storage and callbacks. Hard limit stops safely.
9. Kill switches for system, project, connector, node, provider, callbacks and
   memory writes. UI distinguishes pause, disable, revoke and deprovision.
10. Observability exports OpenTelemetry-compatible traces/metrics and structured
    redacted logs. Default dashboards show availability, latency, errors, denials,
    cost, queue, callback, model and policy metrics.
11. Accessibility, mobile diagnostics, empty/degraded states and no fake demo data.

## Acceptance

- [x] Operator can pair, validate, enable, supervise, pause and rotate safely
- [x] UI offers no arbitrary connector or secret read
- [x] Every action links to audit and correlation
- [x] Hard budget and kill switch stop new work promptly
