# Prompt 525 / CAS-09: Expose jobs, playbooks, channels, and data plane

**Status: COMPLETED 2026-08-08**
**Series:** 516-531
**Depends on:** 517, 522
**Blocks:** 531
**Writing style:** plain ASCII only.

## Goal

Expose async jobs, playbooks, operator channels, and data-plane capabilities so
Carina/Aiva consume Keprix beyond single-turn chat.

## Must-haves

1. Nodes/jobs: playbook.start, playbook.status, jobs.create/cancel, channel.notify
   (Telegram/operator), data.datasets.list, data.jobs.*, export Soft Wall.
2. Job status visible in Carina/Aiva UI (poll or SSE) with deep links.
3. Playbooks use Keprix runtime; product entitlement gates which playbooks appear.
4. Channel outbound Soft Wall / kill switch respected.
5. Data plane does not expose other tenants' datasets.
6. Document "Cookbook" as internal only; user-facing term remains Playbook.
7. Tests: cancel is idempotent; job survives product restart; export Soft Wall.

## Acceptance

- [ ] Operator can start and cancel a Keprix job from Carina UI
- [ ] Playbook list respects Aiva vs Carina entitlements
- [ ] Data export blocked across workspaces

## Done When

Async Keprix depth is reachable from the product shell.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
