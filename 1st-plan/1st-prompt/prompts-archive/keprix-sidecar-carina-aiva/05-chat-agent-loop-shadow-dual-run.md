# Prompt 521 / CAS-05: Chat and agent loop shadow dual-run

**Status: COMPLETED 2026-08-08**
**Series:** 516-531
**Depends on:** 518, 520
**Blocks:** 522
**Writing style:** plain ASCII only.

## Goal

Run the same redacted chat turn on Carina TS engine and Keprix sidecar in shadow
mode, compare quality/safety, and never let shadow output publish side effects.

## Must-haves

1. Feature flag `carina_keprix_shadow` (workspace + global).
2. Primary path remains current engine; shadow invokes Keprix `agent.run`.
3. Store comparison: latency, cost, tool calls, refusal reasons, policy denies,
   hallucination markers (empty tool result then invented facts).
4. Shadow path uses read-only / Soft Wall-block for mutate tools by force.
5. Dual-write memory prohibited; Keprix may keep ephemeral shadow traces only.
6. Operator UI (OPS or Carina admin) to sample comparisons; no customer-facing
   "two answers" confusion unless explicitly opted.
7. Metrics and kill switch for shadow volume.
8. Tests: shadow never calls outbound email/Telegram publish; comparison record written.

## Acceptance

- [ ] Shadow output cannot enroll CRM, send outreach, or book
- [ ] Primary user reply unchanged by shadow failure
- [ ] Comparison artifacts are workspace-scoped

## Done When

522 can promote Keprix to primary with evidence thresholds.

## What was built

- Product sidecar `/v1/products/{carina|aiva}` with capability catalog
- Southbound Carina `/api/keprix/v1/*`, token exchange, Soft Wall, shadow, OPS probe
- Tests: `tests/product_sidecar/test_carina_aiva_sidecar.py`
- Docs: gap map, security, sign-off, operator migration
