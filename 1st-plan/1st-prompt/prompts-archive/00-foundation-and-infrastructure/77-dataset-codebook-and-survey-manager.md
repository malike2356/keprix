# keprix - Prompt 77: Dataset, Codebook, and Survey Manager

> **Status (2026-07-05):** Implemented `src/keprix/research_workspace/datasets/` (importers, codebook, transforms, lineage, exports), `/api/research/datasets/*`, DatasetManager and CodebookPanel UI, `docs/research/dataset-codebook-manager.md`, and 8 new tests (36 total in `tests/research_workspace/`).

## Context

Research and statistical workflows need clean datasets, variable metadata, labels, missing-value handling, and reproducible codebooks. This prompt creates the dataset layer used by PSPP, jamovi, R, Python, and reports.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/research_workspace/datasets/
  __init__.py
  dataset.py
  importers.py
  codebook.py
  variables.py
  missing_values.py
  transforms.py
  validation.py
  export.py
  lineage.py
frontend/src/components/research/DatasetManager.tsx
frontend/src/components/research/CodebookPanel.tsx
tests/research_workspace/test_dataset_importers.py
tests/research_workspace/test_codebook.py
tests/research_workspace/test_missing_values.py
tests/research_workspace/test_dataset_export.py
docs/research/dataset-codebook-manager.md
```

## Supported Inputs

Support:

- CSV.
- TSV.
- Excel.
- JSON.
- Parquet.
- SQLite table export.
- Postgres query export.
- SPSS `.sav` import through optional libraries where available.
- PSPP syntax and data files where available.

## Codebook Model

Store:

- Variable name.
- Label.
- Type.
- Measurement level.
- Value labels.
- Missing value codes.
- Derived variable expression.
- Source column.
- Validation rules.
- Notes.

## Data Safety

- Never mutate original uploaded data.
- Store imported data as versioned derived datasets.
- Record all transformations.
- Redact sensitive values in logs.
- Support sample previews without exposing full private datasets.

## Exports

Export:

- Clean CSV.
- Parquet.
- JSON schema.
- PSPP syntax.
- R script.
- Python notebook cell.
- jamovi-ready CSV and metadata notes.

## Acceptance Criteria

- A CSV can be imported and assigned a codebook.
- Missing values and labels survive export.
- Transformations are recorded as lineage.
- PSPP and jamovi prompts can consume the dataset manager output.
- Tests cover imports, labels, missing values, and exports.
