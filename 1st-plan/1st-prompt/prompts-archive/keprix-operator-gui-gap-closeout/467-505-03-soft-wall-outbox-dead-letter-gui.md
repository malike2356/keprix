# Prompt 470 / 03: Soft Wall outbox and dead-letter GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

**Depends on:** 467, Soft Wall send path

## What was built

- Soft Wall safety GUI wave: `/outreach/deliverability`, `/outreach/outbox`, `/outreach/suppressions`, `/outreach/contactability`, `/outreach/merges`, `/outreach/settings`
- CRM API extensions: deliverability rates/block, outbox retry/cancel, suppressions undo/bulk, merge reject
- Client helpers in `frontend/src/lib/crm-api.ts`; tabs in `OutreachTabNav`
- Docs: `docs/features/soft-wall-safety.md`
- Tests: `tests/frontend/test_soft_wall_safety_gui.py`

**Blocks:** 505

## Goal

Transactional outbox / idempotent sends must be visible. Retries must not be
silent curl ops.

## Must-haves

1. Route `/outreach/outbox` (CRM `/crm/outbox` can reuse component per 466).
2. Table: status (pending/sent/failed/dead_letter), recipient, campaign/step,
   idempotency key, attempts, last error, timestamps.
3. Actions: Soft Wall-gated retry dead-letter; cancel pending; open lead/CRM.
4. Filters: campaign, status, date.
5. Backend: expose outbox store via `/api/outreach/outbox` (or extend existing)
   if not already public; never invent a second send path.
6. Deduped retry proof in tests.
7. Nav entry + Soft Wall panel badge count for dead letters.

## Acceptance

- [x] Dead-letter visible and Soft Wall retryable
- [x] Retry with same idempotency key does not double-send
- [x] Empty state honest

## Done When

Operators can recover failed sends without engineering.
