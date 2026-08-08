# Prompt 484 / 17: Data plane datasets GUI under /data (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/data?tab=datasets` catalog/import/query/versions/delete
- `frontend/src/lib/data-plane-api.ts`; data-planes.md GUI section


**Depends on:** 467, existing `/api/data`
**Blocks:** 485, 487, 503

## Goal

`/api/data` catalog/import/query exists; `/data` workspace tabs do not call it.
Add datasets tab and operator UX.

## Must-haves

1. Extend Data workspace: tab `datasets` (update `DATA_SECTIONS` /
   `DataSectionTabs` / `parseDataTab`).
2. Client `frontend/src/lib/data-plane-api.ts` calling `/api/data/*` only.
3. UI panels:
   - Catalog table (id, name, format, versions, updated)
   - Upload wizard (CSV/Parquet/Excel/SPSS per supported suffixes)
   - Version history drawer
   - SQL query console (read-only; row limit; timeout; error honesty)
   - Planes status / integrity (control vs data plane)
   - Export dataset copy action
4. Soft Wall or confirm for destructive delete; never cross-workspace.
5. Loading/empty/error states; large result pagination.
6. Preserve existing tabs: rag, models, video, analytics, usage, observability.
7. Nav: Data already present; ensure datasets is default-discoverable (docs +
   first-run tip optional).
8. pytest + frontend smoke; docs GUI section in `docs/operations/data-planes.md`.
9. Feature flag if data plane disabled: honest locked panel.

## Acceptance

- [x] Operator imports CSV and runs a constrained query from GUI
- [x] Catalog matches `/api/data/catalog`
- [x] Existing `/data` tabs still work
- [x] Delete Soft Wall/confirm gated

## Done When

Data plane is not API-only.
