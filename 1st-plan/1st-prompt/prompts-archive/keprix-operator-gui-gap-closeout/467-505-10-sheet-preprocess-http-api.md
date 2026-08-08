# Prompt 477 / 10: Sheet preprocess HTTP API + Soft Wall hooks (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- Confirmed `/api/crm/sheets` + `/api/sheet-preprocess` (upload/propose/apply/download)
- Soft Wall kind `sheet.preprocess.apply` on apply
- Tests: `tests/crm/test_sheet_preprocess_routes.py` (5 passed)


**Depends on:** 467, `src/keprix/sheet_preprocess/` library
**Blocks:** 478
**Aligns with:** CRM 433-434

## Goal

Expose the existing sheet preprocess library over HTTP with Soft Wall before
apply. Today: library + tests only; no routes.

## Must-haves

1. Router `/api/crm/sheet` or `/api/sheet-preprocess/*`:
   upload, propose, get job, apply (gated), download enriched file.
2. Soft Wall approval type `sheet.preprocess.apply`.
3. Empty-cell-only fill; never overwrite non-empty without Soft Wall exception
   path (default deny).
4. Provenance per filled cell; cost estimate; workspace isolation.
5. Job records listable for 478/480.
6. Agent tools propose/apply (apply Soft Wall).
7. pytest for propose/apply/reject; TestClient auth.
8. OpenAPI honest.

## Acceptance

- [x] Upload -> propose -> Soft Wall apply creates durable result
- [x] Reject leaves store unchanged
- [x] Cross-workspace denied

## Done When

478 can build GUI on stable API.
