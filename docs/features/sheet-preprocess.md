# Spreadsheet preprocess (sheet enrich)

Domain-agnostic CSV/XLSX ingest, column role mapping, blank-cell fill proposals,
Soft Wall gated apply, and optional CRM upsert. Property is one sheet type among
many (`generic`, `leads`, `tenant_list`, `property_data`, plus pack registry hooks).

## Operator UI

Canonical route: `/crm/enrich` (CRM Enrich tab when CRM nav is on).

Flow:

1. Upload CSV, TSV, or XLSX
2. Propose (auto column roles + optional model fills; CRM upsert plan when mapped)
3. Review blank report, column mapper, and proposed-fill diff
4. Soft Wall Approve / Reject
5. On approve: apply empty-cell fills only, write enriched file, optionally upsert
   CRM accounts/leads/contacts and create a result list
6. Deep links: `/crm/enrich?job={id}`, list link, `/crm/leads`

Reject leaves the enrichment job and CRM store unchanged.

## HTTP API

Primary prefix: `/api/crm/sheets`  
Alias: `/api/sheet-preprocess` (same handlers)

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/upload` | Multipart `file` |
| POST | `/propose` | Creates `crm_enrichment_jobs` row + proposal |
| GET | `/` | List jobs |
| GET | `/{job_id}` | Job + metrics |
| POST | `/{job_id}/apply` | Soft Wall kind `sheet.preprocess.apply` (alias of apply_enrichment) |
| GET | `/{job_id}/download` | Enriched CSV after apply |
| GET | `/email-ingest/status` | Env-gated stub status |

Soft Wall payload deep links use `/crm/enrich?job=...&approval=...`.

Workspace isolation: uploads and outputs live under a workspace-scoped directory
(`KEPRIX_SHEET_PREPROCESS_DIR` or `$KEPRIX_HOME/sheet_preprocess/{workspace}`).
Absolute paths outside that tree are denied unless `KEPRIX_SHEET_ALLOW_ABS=1`.

## Agent tools

Toolset: `crm`

- `sheet_preprocess_propose` - propose only; returns `deep_link` `/crm/enrich?job=`
- `sheet_preprocess_apply` - Soft Wall gated (or `force`); returns enrich / list / leads deep links

Import: `import keprix.tools.sheet_preprocess_tools` (registers on import).

## Email ingest (optional, disabled by default)

Module: `keprix.sheet_preprocess.email_ingest`

```bash
KEPRIX_SHEET_EMAIL_INGEST=0   # default: off
```

When set to `1`, operators can enable an IMAP poller stub. Today the stub returns
`skipped` until credentials and poller body are configured. Ingested attachments
must still go through propose + Soft Wall apply before any CRM write. Jobs appear
on `/crm/jobs` as enrichment jobs with type `sheet_preprocess`.

## Library

Package: `src/keprix/sheet_preprocess/`

- Propose/apply: empty cells only; never overwrite non-blank values
- Safety: size/row/column limits, formula warnings, CSV injection escaping, content hashes
- CRM plan: plan-only until Soft Wall apply executes upserts

## Metrics (UI)

Blank cells, proposed fills, cells filled/skipped, rough cost estimate
(heuristic, not billing), job status.

## Tests

```bash
pytest tests/sheet_preprocess tests/crm/test_sheet_preprocess_routes.py -q
```
