# Prompt 471 / 04: Soft Wall / CRM suppressions manager GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

**Depends on:** 467

## What was built

- Soft Wall safety GUI wave: `/outreach/deliverability`, `/outreach/outbox`, `/outreach/suppressions`, `/outreach/contactability`, `/outreach/merges`, `/outreach/settings`
- CRM API extensions: deliverability rates/block, outbox retry/cancel, suppressions undo/bulk, merge reject
- Client helpers in `frontend/src/lib/crm-api.ts`; tabs in `OutreachTabNav`
- Docs: `docs/features/soft-wall-safety.md`
- Tests: `tests/frontend/test_soft_wall_safety_gui.py`

**Blocks:** 475, 503
**Aligns with:** CRM 448

## Goal

Suppression must be manageable in GUI (email/phone/telegram, reason, permanent).

## Must-haves

1. Route `/outreach/suppressions` and shared component for `/crm/suppressions`.
2. CRUD Soft Wall-gated for bulk import; single add with reason.
3. Search, filter by channel/reason, export for DSAR.
4. Enroll and send paths already refuse suppressed; UI shows blocked count on
   enroll preflight (475).
5. Unsubscribe/bounce auto-entries visible with source.
6. Tests: suppressed never enrolls; GUI lists entry after bounce fixture.
7. Nav + docs `docs/features/crm-compliance.md` or Soft Wall compliance section.

## Acceptance

- [x] Operator adds/removes suppression from GUI
- [x] Bulk CSV import Soft Wall preview
- [x] Auto bounce/unsubscribe appears without manual entry

## Done When

Compliance ops are not API-only.
