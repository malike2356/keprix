# Prompt KSF-03: Provisioning, events, jobs, resilience, and operations

**Status: COMPLETED 2026-08-08**
**Depends on:** KSF-00 through KSF-02
**Blocks:** all product provisioning/sign-off prompts

## Build

1. CLI: `keprix product provision|plan|status|upgrade|rollback|disable|remove`.
   Declarative plans, dry-run, idempotency, locks, receipts and last-known-good.
2. Provision namespace, workload identity, connector allowlist, callbacks, signing
   keys, pack migrations, memory policy, budgets, queues, health and feature flag.
3. Durable CloudEvents-style inbox/outbox with signature, dedupe, cursor,
   acknowledgement, retry, dead-letter and deletion events.
4. Durable job service with state machine, checkpoint, progress, cancellation,
   attempt, retry, budget, result reference, TTL and crash recovery.
5. Per-product/deployment/tenant/node rate, concurrency, cost and queue limits;
   circuit breakers and kill switches; dependency health and degraded labels.
6. Metrics, traces and audit are product-scoped and content-redacted. Operator
   status shows pack/contract/product compatibility and actionable failures.
7. Backup/restore excludes secrets and transient sensitive payloads; key rotation,
   deprovision and deletion completion are tested.

## Acceptance

- [ ] Repeated provision produces no duplicate identity/callback/migration
- [ ] Crash/retry cannot duplicate event or external action
- [ ] Product kill switch stops new work and preserves investigation state
- [ ] Rollback restores last compatible pack and schemas

## What was built

- Shared product sidecar foundation under `src/keprix/product_sidecar/`
- Fixture packs + registry install/validate/upgrade/rollback/kill
- Northbound `/v1/products/{product_key}` including events/stream and durable jobs
- Southbound ProductConnector with SSRF/default-deny and FakeProductConnector
- CLI: `keprix product provision|plan|status|upgrade|rollback|disable|remove|conformance`
- Conformance gate + release runbook `docs/architecture/product-sidecar-foundation-release.md`
- Tests: `tests/product_sidecar/test_sidecar_foundation.py` (plus existing Carina/Aiva suite)
