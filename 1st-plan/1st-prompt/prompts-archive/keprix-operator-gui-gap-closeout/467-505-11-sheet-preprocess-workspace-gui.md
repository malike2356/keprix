# Prompt 478 / 11: Sheet preprocess workspace GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- Operator GUI `/crm/enrich` (upload, map, Soft Wall apply/reject, job list)
- Nav `crm-enrich` in navigation.py + navigation.ts
- `/data?tab=sheets` redirects to `/crm/enrich`
- Docs: `docs/features/sheet-preprocess.md`
- Tests: `tests/frontend/test_sheet_enrich_gui.py`


**Depends on:** 477
**Blocks:** 505
**Aligns with:** CRM 434/466

## Goal

Operators review AI column maps and proposed fills in GUI.

## Must-haves

1. Canonical route `/crm/enrich` (create CRM shell pages if CRM UI not yet
   shipped; temporary `/data?tab=sheets` must redirect to same UX).
2. Screens: upload, column mapper, blank report, proposed-fill diff, job status,
   Soft Wall Approve/Reject, link to resulting list/leads.
3. Nav under CRM or Data until CRM nav lands; sync both contracts.
4. Deep links from agent tools and Soft Wall approvals.
5. Metrics visible (blank, filled, cost).
6. Frontend smoke tests.
7. Docs `docs/features/sheet-preprocess.md`.

## Acceptance

- [x] Happy path fully from GUI
- [x] Reject leaves CRM/store unchanged
- [x] Nav entry when flag on

## Done When

Sheet enrich is not library-only.
