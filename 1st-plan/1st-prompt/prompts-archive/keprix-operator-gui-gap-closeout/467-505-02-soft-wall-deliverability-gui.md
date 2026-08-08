# Prompt 469 / 02: Soft Wall deliverability dashboard (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

**Depends on:** 467, existing Soft Wall outreach

## What was built

- Soft Wall safety GUI wave: `/outreach/deliverability`, `/outreach/outbox`, `/outreach/suppressions`, `/outreach/contactability`, `/outreach/merges`, `/outreach/settings`
- CRM API extensions: deliverability rates/block, outbox retry/cancel, suppressions undo/bulk, merge reject
- Client helpers in `frontend/src/lib/crm-api.ts`; tabs in `OutreachTabNav`
- Docs: `docs/features/soft-wall-safety.md`
- Tests: `tests/frontend/test_soft_wall_safety_gui.py`

**Blocks:** 474, 475, 503

## Goal

Operators see sender readiness, bounce/complaint rates, warm-up notes, and
domain authentication guidance before cold send. Today Soft Wall campaigns UI
exists but deliverability is not a first-class page.

## Must-haves

1. Route `/outreach/deliverability` (also link from `/crm/deliverability` when
   CRM 466 ships; shared component OK).
2. Backend: extend Soft Wall / email settings APIs if needed for:
   - verified sender domains
   - SPF/DKIM/DMARC status hints (honest unknown vs verified)
   - bounce rate, complaint rate, unsubscribe rate (period)
   - warm-up flags / daily send budget remaining
3. UI: checklist, rates cards, campaign filter, Soft Wall gate when rates exceed
   policy thresholds.
4. Nav under Soft Wall / Outreach group.
5. Kill-switch deep link to 474 settings.
6. Tests + empty zeros (no fake demos).
7. Docs in Soft Wall / outreach features doc.

## Acceptance

- [x] Operator sees sender readiness before launching cold campaign
- [x] Threshold breach blocks Soft Wall approve with clear reason
- [x] Nav entry present

## Done When

Cold send cannot ignore deliverability because UI hid it.
