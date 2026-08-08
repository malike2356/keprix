# Prompt 455 / N05: Template experimentation (A/B)

**Status: COMPLETED 2026-08-08** (P5 Nice)  
**Series:** 429-465  
**Depends on:** 444, 447, 448  
**Blocks:** none  
**Writing style:** plain ASCII only.

## What was built

- Template A/B Soft Wall promote

## Goal

Template experimentation with fixed cohorts, minimum sample warnings, and guard metrics.

## Must-haves

1. Experiment object: variants (subject/body), traffic split, start/end, linked sequence.
2. Fixed cohort assignment (sticky per contact).
3. Metrics: send, reply, positive reply, unsub, complaint, book.
4. Guardrails: auto-pause if complaint/unsub rate exceeds workspace threshold; Soft Wall notify.
5. UI: create experiment, results table, winner Soft Wall promote.
6. Minimum sample warning before declaring winner.
7. Tests: sticky assignment; pause on guard breach.

## Acceptance

- [x] Two subjects A/B with even split
- [x] Winner promote updates sequence template under Soft Wall
- [x] Guard pause stops losing/winning sends as configured

## Done When

Copy tests are measurable without risking deliverability.
