# Prompt ABS-03: ABBIS provisioning, entitlements, localisation, and resilience

**Status: COMPLETED 2026-08-08**
**Depends on:** ABS-02, ABBIS prompt 95
**Blocks:** ABS-05

## What was built

- provisioning.plan/provision/upgrade/rollback
- Localisation en/tw/ha
- Degraded AI queue with stale-authority replay rejection


## Goal

Provision a sidecar for each ABBIS deployment and tenant policy while supporting
Ghana field conditions, modular accessories and safe degraded operation.

## Must-haves

1. `keprix product provision abbis` negotiates product/pack/mesh versions,
   installs manifests, creates namespaces, workload identity, callbacks, policies,
   queues, RAG indexes and a secret-free receipt.
2. Entitlements are fetched from ABBIS on session and dangerous action; product
   feature flags/accessories control node visibility and execution.
3. Bootstrap only stakeholder-appropriate assistants, languages, channels and
   context. Onboarding choices can be changed without cross-tenant reindexing.
4. Support English plus configured Ghana languages through product localisation;
   voice/text fallback and confirmation of numbers, units, dates and money.
5. Sidecar-down follows spec 28/prompt 95: product core continues, eligible AI
   work queues with TTL/priority/dedupe, status is visible, and replay revalidates
   permissions, record version and approval.
6. Low-bandwidth mode uses compact schemas, resumable upload, bounded audio,
   asynchronous result references and no repeated model call after reconnect.
7. Per-tenant budgets, quotas and retention; encryption; regional deployment
   documentation; deletion propagation; backup and restore.
8. Upgrade/rollback validates all mesh manifests and never enables an accessory
   or cross-tenant aggregate automatically.

## Acceptance

- [x] New tenant provisions only entitled assistants and nodes
- [x] Offline queue replay cannot use stale authority
- [x] Localised confirmations preserve numeric/domain meaning
- [x] Upgrade and rollback retain tenant isolation
