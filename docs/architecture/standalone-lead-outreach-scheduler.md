# Standalone lead outreach: durable campaign sequence scheduler (Prompt 624)

**Status:** IMPLEMENTED  
**Date:** 2026-08-09  
**Depends on:** Prompt 622 durable CRM/outreach storage

## Purpose

Process due sequence enrollments without in-memory timers. Workers claim rows with short leases so restarts and horizontal scaling neither lose nor duplicate work. Soft Wall parks a step at `awaiting_approval` without advancing `current_step`. Live email delivery remains Prompt 625.

## Claim lease

1. Tick calls `claim_due_enrollments(now, limit, worker_id, lease_seconds)`.
2. Only `status=active` rows with `next_run_at <= now` and expired/null `locked_until` are eligible.
3. SQLite: select candidates, then CAS `UPDATE ... WHERE id=? AND lease free` under store lock.
4. Postgres: prefer `FOR UPDATE SKIP LOCKED` when available; otherwise same CAS loop.
5. On terminal handling for that tick (advance, park, defer, stop, backoff, dead letter), clear `locked_until` / `locked_by`.
6. Stale leases are reclaimable by the next claim (optional `reclaim_stale_enrollment_locks`).

## Soft Wall park

- Create idempotent draft message (`idempotency_key=enrollment:{id}:step:{n}`).
- Create Soft Wall approval; set enrollment `awaiting_approval`; clear `next_run_at`; **do not** advance `current_step`.
- Approve path revalidates suppression, pause, daily cap, reply/booking stops before send/advance.
- Reject stops the enrollment (default `cancelled`) without advancing.

## Backoff and dead letters

- Transient send failure: `attempt_count += 1`, `next_run_at = now + min(2**attempt, 3600) + jitter`.
- Permanent failure or max attempts (`KEPRIX_OUTREACH_MAX_ATTEMPTS`, default 8): `dead_letter` + `last_error` + `dead_letter_at`.
- Operator retry: `POST /api/outreach/enrollments/{id}/retry`.

## Business hours and daily cap

- Outside Mon-Fri 09-17 (campaign TZ): defer to next weekday 09:00 (not +1h thrash).
- Daily cap hit: defer to next midnight in campaign TZ and release lease.

## Surfaces

| Surface | Path |
| --- | --- |
| Store | `src/keprix/outreach/store.py` (`claim_*`, health, controls) |
| Tick | `src/keprix/outreach/scheduler.py` → `run_scheduler_tick` / `OutreachService.process_due` |
| HTTP | `POST /api/outreach/process-due`, `GET /api/outreach/scheduler/health` |
| CLI | `keprix outreach-scheduler tick\|health` |
| Cron seed | `outreach-process-due` prompt (still calls `outreach_process_due`) |
| UI | Outreach control center chips (queue, dead letters, oldest due) |

## Honesty

- Scheduling / process-due: **REAL** (claim lease + Soft Wall park + tests).
- Live email send: still **PARTIAL** until Prompt 625.
