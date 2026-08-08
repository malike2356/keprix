# Prompt 495 / 28: Eval benchmarks GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/evals` benchmarks section wired to `/api/evals/benchmarks`


**Depends on:** 467, `/api/evals` + `/api/evals/benchmarks`, existing `/evals`
**Blocks:** 505

## Goal

Wire benchmarks API into `/evals` (or child route) so suites are operable.

## Must-haves

1. Benchmarks tab/section on `/evals`.
2. List suites, run Soft Wall/confirm, view results history.
3. Frontend must call `/api/evals/benchmarks` (today unreferenced).
4. Tests + docs.

## Acceptance

- [x] Operator runs a benchmark suite from GUI
- [x] Results visible historically

## Done When

Benchmarks are not hidden API.
