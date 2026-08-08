# Prompt XCS-02: Xeclone product API, Carina bridge, and dual-run

**Status: COMPLETED 2026-08-08**
**Depends on:** XCS-00, XCS-01
**Blocks:** XCS-03 through XCS-05

## Goal

Implement a temporary, observable bridge that moves reasoning to Keprix before
moving OAuth, inbound webhooks or approval UI away from Carina.

## Must-haves

1. Common product-side health, capabilities, token exchange, context and event ack.
2. Reads for canonical persona/version, consent eligibility, content calendar,
   channel connection status, inbound item by id, approval item, performance
   summary and product-owned artifact references. Never expose bulk private corpus.
3. Actions: create draft/approval, attach artifact reference, update schedule,
   record generation, publish approved item and acknowledge inbound. Product or
   Carina revalidates approval, consent, channel and idempotency.
4. Bridge passes `worker_id`, `persona_version`, `approval_id`, `keprix_run_id`,
   tenant and correlation ids. It does not copy OAuth tokens into requests.
5. Shadow mode sends the same redacted input to Carina and Keprix, stores quality/
   safety comparison, and never publishes the shadow output.
6. Dual-write memory is prohibited. Define authority per wave: Keprix draft memory
   only in Wave 1; explicit migration and read-only Carina history in Wave 2.
7. Webhook ingress remains Carina until Wave 2 contract and replay tests pass.
8. Circuit breaker falls back to current Carina behaviour without duplicate draft,
   approval, notification or publish action.
9. Instrument latency, cost, output comparison, persona drift, denial and fallback.

## Acceptance

- [ ] Keprix draft enters existing approval UI without changing live inbound path
- [ ] Shadow output can never publish
- [ ] Fallback does not create duplicate approvals or sends
- [ ] No OAuth or bulk private archive crosses the bridge

## What was built

- Northbound `/v1/products/xeclone/*` + fixture product API
- Shadow dual-run that never publishes; bridge draft into approvals

