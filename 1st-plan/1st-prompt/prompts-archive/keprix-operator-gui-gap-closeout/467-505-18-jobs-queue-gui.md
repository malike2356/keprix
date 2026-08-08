# Prompt 485 / 18: Background jobs queue GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/data?tab=jobs` cancel/retry Soft Wall; cancel+retry API routes
- `frontend/src/lib/jobs-api.ts`; `tests/jobs/test_cancel_retry.py`


**Depends on:** 484 (shared Data IA) or 467
**Blocks:** 505

## Goal

Surface `/api/jobs` for operators: status, retry, cancel, dead letters.

## Must-haves

1. `/data?tab=jobs` and/or `/admin/jobs` (prefer Data tab + admin deep link).
2. Table: job type, status, workspace, created/updated, error, attempts.
3. Actions: cancel, retry Soft Wall-gated for side-effecting jobs.
4. Link related objects (sheet job, discovery job, builder job).
5. Client for `/api/jobs`; tests; empty state.
6. Badge on Data nav when dead letters > 0 (optional Nice: live poll).

## Acceptance

- [x] Operator sees and retries dead-letter jobs from GUI
- [x] Cancel works for running/queued

## Done When

Job ops are not hidden in API.
