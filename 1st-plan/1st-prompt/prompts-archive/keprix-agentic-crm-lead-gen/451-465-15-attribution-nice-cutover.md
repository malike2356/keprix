# Prompt 465 / N15: Attribution models and Nice wave cutover

**Status: COMPLETED 2026-08-08** (P5 Nice)  
**Series:** 429-465  
**Depends on:** 447, 445, Nice prompts intended to ship in this wave  
**Blocks:** none  
**Writing style:** plain ASCII only.

## What was built

- Attribution + agentic-crm-nice-signoff.md

## Goal

Attribution that distinguishes sourced, influenced, and closed revenue; plus Nice-wave docs/tests cutover note (does not archive Must 450).

## Must-haves

1. Attribution modes: `sourced`, `influenced`, `closed` on Deal; link optional Stripe customer id **read-only** (no new prices).
2. Report UI: pipeline by attribution mode; cost per qualified opportunity (from enrich/send metrics).
3. Guard: vanity sends alone insufficient (align hardening review metrics).
4. Docs update: Nice features matrix (shipped vs stub).
5. pytest for attribution assignment rules.
6. Sign-off addendum `docs/architecture/agentic-crm-nice-signoff.md` (separate from Must 450).

## Acceptance

- [x] Deal can be marked influenced vs sourced
- [x] Report excludes vanity-only success
- [x] Nice sign-off lists each 451-464 status

## Done When

P5 wave is accountable without blocking Must archive rules.
