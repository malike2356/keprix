# Prompt 436 / 07: Discovery adapter framework + job runner

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 430  
**Blocks:** 437-441  
**Writing style:** plain ASCII only.

## What was built

- src/keprix/discovery/ adapters + Soft Wall materialize
- /crm/discover + /crm/jobs UI
- tests/discovery


## Goal

Pluggable discovery adapters that produce normalized lead candidates and write DiscoveryJob records.

## Must-haves

1. Package `src/keprix/discovery/`.
2. Adapter interface: `name`, `domain_packs`, `discover(query, limits) -> list[LeadCandidate]`, `health()`.
3. LeadCandidate fields: company, contacts[], urls, geo, source, external_id, raw, score_hint.
4. Job runner: async/cron capable; status queued/running/done/failed; Soft Wall before list materialize (configurable).
5. Egress allowlist integration; rate limit per adapter.
6. Registry + feature flags per adapter.
7. Tests with fake adapter.
8. Adapter manifest declares terms/licence reference, permitted purpose, allowed
   fields, retention, jurisdiction, contact-use eligibility, and health status.
9. Durable checkpoints, cancellation, cost forecast/budget, retry with jitter,
   circuit breaker, dead-letter state, provenance per field, and content hashes.
10. Discovery produces candidates only. A separate policy decision determines
    whether each person/channel/purpose is contactable.
11. **GUI (with 466):** job list/detail at `/crm/jobs` must expose status,
    adapter health, cancel, resume, cost estimate, Soft Wall materialize, and
    dead-letter retry. API-only job control is not Done.

## Acceptance

- [x] Fake adapter end-to-end creates Enrichment-ready List draft
- [x] Failed jobs do not partial-corrupt without resume cursor
- [x] Adapter not configured returns honest error
- [x] Operator can see job history and cancel/retry from `/crm/jobs` (466)

## Done When

Vertical adapters can register without changing CRM core; jobs are viewable.
