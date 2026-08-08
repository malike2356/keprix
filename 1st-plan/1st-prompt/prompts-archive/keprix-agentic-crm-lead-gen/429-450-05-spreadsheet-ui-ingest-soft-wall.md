# Prompt 434 / 05: Spreadsheet UI + ingest + Soft Wall apply

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 433, 431  
**Blocks:** 442  
**Writing style:** plain ASCII only.

## What was built

- /api/crm/sheets + /crm/enrich UI Soft Wall apply
- sheet_preprocess tools + email ingest stub
- docs/features/sheet-preprocess.md


## Goal

Operators and agents can ingest sheets, review AI column maps, Soft Wall approve, apply fills, and upsert CRM.

## Must-haves

1. API: upload, propose, get job, apply (gated), download enriched file.
2. Canonical UI route `/crm/enrich` (nav + Soft Wall deep link). Optional
   `/data?tab=sheets` alias only if it redirects to the same review UX.
3. Screens: upload, column mapper, blank report, proposed-fill diff, job status,
   Soft Wall Approve/Reject, link to resulting List/leads.
4. Optional email-ingest worker (IMAP) **inside Keprix** (env-gated), inspired by
   Carina monitor.py; Soft Wall still required before CRM write. Ingest jobs
   appear on `/crm/jobs` with type `sheet_preprocess`.
5. Agent tool: `sheet_preprocess_propose` / `sheet_preprocess_apply` (apply
   requires Soft Wall or elevated flag); tools must return workspace deep links.
6. Metrics: cells blank, cells filled, cost estimate (visible in UI, not logs only).
7. Docs: `docs/features/sheet-preprocess.md`.

## Acceptance

- [x] Happy path: upload leads CSV -> propose -> approve -> CRM leads created from GUI
- [x] Reject leaves store unchanged
- [x] Email path documented; can be disabled
- [x] Enrich nav entry present when CRM flag on

## Done When

Discovery outputs can also land as sheets for the same review UX.
