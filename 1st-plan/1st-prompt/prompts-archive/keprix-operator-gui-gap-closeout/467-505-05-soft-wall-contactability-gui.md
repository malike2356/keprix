# Prompt 472 / 05: Contactability decisions GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

**Depends on:** 467, 471

## What was built

- Soft Wall safety GUI wave: `/outreach/deliverability`, `/outreach/outbox`, `/outreach/suppressions`, `/outreach/contactability`, `/outreach/merges`, `/outreach/settings`
- CRM API extensions: deliverability rates/block, outbox retry/cancel, suppressions undo/bulk, merge reject
- Client helpers in `frontend/src/lib/crm-api.ts`; tabs in `OutreachTabNav`
- Docs: `docs/features/soft-wall-safety.md`
- Tests: `tests/frontend/test_soft_wall_safety_gui.py`

**Blocks:** 475, 503
**Aligns with:** CRM 430/448/466

## Goal

Discovery is not contact permission. Operators need person x channel x purpose
decisions visible and Soft Wall-editable.

## Must-haves

1. Route `/outreach/contactability` (+ `/crm/contactability` alias).
2. Grid/table: person/entity, channel, purpose, jurisdiction, decision
   (allow/deny/needs_review), policy version, evidence, expiry.
3. Bulk Soft Wall approve/deny; never auto-allow from discovery alone.
4. Link from discovery job results and enroll preflight denials.
5. Store/API if missing: add under Soft Wall or CRM package; workspace-scoped.
6. Tests for deny blocks enroll UI with reason.
7. Docs: contactability vs consent distinction.

## Acceptance

- [x] Deny blocks enroll with GUI reason + deep link
- [x] Needs_review Soft Wall queue visible
- [x] Discovery success does not imply contactable

## Done When

Operators can separate "found" from "may contact".
