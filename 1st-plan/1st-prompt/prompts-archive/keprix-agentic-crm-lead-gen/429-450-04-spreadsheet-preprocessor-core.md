# Prompt 433 / 04: Spreadsheet preprocessor core

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 430  
**Blocks:** 434, 440, 441  
**Writing style:** plain ASCII only.

**Implementation note:** A tested baseline now exists under
`src/keprix/sheet_preprocess/`. Extend it rather than creating a parallel
processor. This prompt remains pending until all requirements below and the
binding hardening review are complete.

## Why this exists

Port the Carina email spreadsheet enrichment **pattern** into Keprix as a
first-class, domain-agnostic preprocessor (not property-only).

Reference only (do not copy tree):  
`carina/02-backends/workers/spreadsheet-processor/processor.py`

## What was built

- Extended sheet_preprocess: safety, registry, validation, CRM upsert plan
- tests/sheet_preprocess (14 passed)


## Goal

Given a tabular file, classify sheet type, propose or accept column roles, and
fill empty cells with model-assisted enrichment.

## Must-haves

1. Package `src/keprix/sheet_preprocess/`.
2. Ingest CSV/XLSX (reuse analytics file_import helpers where possible).
3. Column role enum: `identity`, `metric`, `enrich_target`, `pii`, `ignore`, `score`, `stage`, `contact_email`, `contact_phone`, `company_name`, `url`.
4. Modes:
   - `user_schema`: caller supplies column->role map and optional metrics list.
   - `auto_analyse`: model proposes type + roles + missing metrics; returns proposal object (no write yet).
5. Built-in types: `generic`, `leads`, `tenant_list`, `property_data`, plus pack registry hook.
6. Fill policy: **empty cells only**; never overwrite user data; confidence optional.
7. Output: enriched dataframe/file path + EnrichmentJob record + optional CRM upsert plan.
8. Batching and token budget limits; fail soft with partial fills.
9. Tests with fixture sheets (leads + generic).
10. Apply `ref-429-programme-hardening-review.md`: file limits, worksheet selection,
    formula safety, content hashes, provenance, structured validation, resumable
    batches, cancellation, export injection safety, and honest flattened-output warnings.

## Acceptance

- [x] Auto propose does not mutate until apply
- [x] User schema respected
- [x] Property is one type among many

## Done When

434 can expose UI/API apply path.
