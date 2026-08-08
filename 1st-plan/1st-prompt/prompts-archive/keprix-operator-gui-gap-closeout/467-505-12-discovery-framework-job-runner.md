# Prompt 479 / 12: Discovery adapter framework + job runner (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- Verified `src/keprix/discovery/` (adapters, runner, materialize, Soft Wall)
- HTTP `/api/crm/discovery*` mounted; pytest `tests/discovery` (15 passed)
- Fake + CH + CSV adapters present


**Depends on:** 467
**Blocks:** 480
**Aligns with:** CRM 436-437

## Goal

Implement `src/keprix/discovery/` with pluggable adapters and durable jobs.
Companies House + CSV first; web/social stubs honest.

## Must-haves

1. Package + adapter interface (name, packs, discover, health, manifest).
2. LeadCandidate normalized model + provenance.
3. Job runner: queued/running/done/failed/dead_letter/cancelled; checkpoints;
   cancel; cost forecast; Soft Wall before list materialize.
4. Egress allowlist + rate limits.
5. Feature flags per adapter; `not_configured` honest.
6. CH adapter wrapping existing integrations; CSV via sheet preprocess schema.
7. Contactability is separate (472); discovery never implies send rights.
8. Tests with fake adapter + mocked CH.
9. HTTP `/api/crm/discovery` or `/api/discovery/*`.

## Acceptance

- [x] Fake adapter creates Soft Wall-ready list draft
- [x] Failed jobs resume via cursor
- [x] Unconfigured adapter honest error

## Done When

480 can surface jobs in GUI.
