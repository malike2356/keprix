# Prompt 474 / 07: Soft Wall kill switches, cadence, budgets settings (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

**Depends on:** 469, Soft Wall

## What was built

- Soft Wall safety GUI wave: `/outreach/deliverability`, `/outreach/outbox`, `/outreach/suppressions`, `/outreach/contactability`, `/outreach/merges`, `/outreach/settings`
- CRM API extensions: deliverability rates/block, outbox retry/cancel, suppressions undo/bulk, merge reject
- Client helpers in `frontend/src/lib/crm-api.ts`; tabs in `OutreachTabNav`
- Docs: `docs/features/soft-wall-safety.md`
- Tests: `tests/frontend/test_soft_wall_safety_gui.py`

**Blocks:** 475, 503

## Goal

Workspace/campaign/domain kill switches and cadence caps must be operable from
GUI with Soft Wall when re-enabling or raising budgets.

## Must-haves

1. Route `/outreach/settings` (safety tab) and/or `/crm/settings` shared.
2. Controls:
   - workspace kill switch (stop all Soft Wall sends)
   - per-campaign kill switch
   - domain rate limits
   - max emails/week/contact
   - quiet hours / timezone
   - enrich + send budgets remaining
3. Soft Wall required to turn kill switch OFF or raise budget above policy.
4. Turning kill switch ON may be immediate for admins (audit always).
5. Status badges on Soft Wall overview and deliverability page.
6. Tests: kill switch stops process_due; Soft Wall on disable.
7. Nav + docs.

## Acceptance

- [x] Kill switch visible and toggleable under Soft Wall rules
- [x] Budgets/cadence editable with audit
- [x] Outreach overview shows when killed

## Done When

Incident response does not require SSH or curl.
