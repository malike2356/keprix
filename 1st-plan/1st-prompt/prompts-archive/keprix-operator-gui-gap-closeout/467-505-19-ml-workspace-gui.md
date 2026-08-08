# Prompt 486 / 19: ML workspace GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/data?tab=ml` experiments/runs/registry; GET `/api/ml/runs`
- `frontend/src/lib/ml-api.ts`


**Depends on:** 484
**Blocks:** 505

## Goal

Surface `/api/ml` experiments/runs/registry in `/data?tab=ml`.

## Must-haves

1. Data tab `ml`.
2. UI: experiments list, run detail metrics, model registry entries, promote /
   Soft Wall if policy requires.
3. Honest empty when ML backend disabled.
4. Wire existing routes only; no second ML stack.
5. Docs + tests.
6. Edition/feature flag if applicable.

## Acceptance

- [x] Operator browses experiments/runs from GUI
- [x] Disabled state honest

## Done When

ML workspace matches data-plane docs for operators.
