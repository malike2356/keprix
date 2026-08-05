# Keprix Prompt 162: Research Tools Frictionless UI

## Purpose

Make PSPP, jamovi, Obsidian, and SPSS (`.sav`) workflows usable by **non-technical
researchers** without reading API docs or knowing backend paths. Keprix already has
backend bridges; this prompt wires them into plain-language UI on `/research`,
`/research/projects/{id}`, and `/analytics`.

Researchers should complete a survey-style workflow in four steps: upload data, run
analysis, export notes, write up results.

## Dependencies

- Prompt 82 (research playbooks UI) shipped.
- Prompt 54 analytics workspace and jamovi bridge shipped.
- Existing routes:
  - `/api/research/pspp/*`
  - `/api/research/obsidian/*`
  - `/api/research/datasets/*`
  - `/api/analytics/jamovi/*`
  - `/api/analytics/parse-file`

## Working directory

`/opt/lampp/htdocs/verlox/keprix`

## What to build

### 1. Backend: SPSS `.sav` on quick analytics upload

Extend `src/keprix/analytics/file_import.py`:

- Accept `.sav` when `pyreadstat` is installed.
- Convert to CSV text (preserve column names).
- Clear error when `pyreadstat` is missing.
- Update `supported_analytics_formats()` and tests.

### 2. Backend: dataset export download

Add `GET /api/research/datasets/{dataset_id}/export/download?format=jamovi|pspp|csv`
in `dataset_routes.py`:

- `jamovi`: zip package via `prepare_export_package` from dataset preview rows.
- `pspp` / `csv`: stream the file produced by existing export helper.
- Auth: `get_current_user` (same as other dataset routes).

### 3. Frontend API helpers

In `research-workspace-api.ts`:

- `fetchPsppStatus()`
- `generatePsppAnalysis(datasetId, procedures?)`
- `runPsppAnalysis(runId, outputFormat?)`
- `downloadResearchDatasetExport(datasetId, format)` (blob download)

In `analytics-api.ts`:

- `downloadJamoviPackage(rows, datasetName?)` (zip blob download)
- `parseCsvToRows(data: string)` helper for jamovi export from textarea

### 4. New UI components

#### `ResearchGettingStarted.tsx`

Four-step guided card at top of project pages:

1. Upload your data (SPSS, Excel, CSV)
2. Run statistical analysis (PSPP or jamovi)
3. Export notes to Obsidian
4. Open full project workspace

Plain language; no jargon in primary labels.

#### `ResearchStatsPanel.tsx`

Shown when a dataset is selected on project pages:

- **PSPP block**
  - Status chip: installed / not installed with setup hint
  - Analysis preset dropdown: Summary tables, Compare groups, Correlations
  - Primary button: **Run analysis** (generate syntax + run in one click)
  - Output preview (tables or syntax-only instructions)
- **jamovi block**
  - **Download for jamovi** button (zip)
  - Short instructions: open zip in jamovi desktop app

#### Upgrade existing panels

- `DatasetManager`: friendlier copy; label SPSS `.sav` support; drag-and-drop zone
- `CodebookPanel`: hide JSON by default behind "Advanced codebook"; keep export buttons
- `ResearchPlaybookRunner`: human summaries per playbook; default dry-run off; recommend
  `pspp_analysis` and `jamovi_preparation` for survey work
- `ObsidianVaultSettings`: guided copy; **Export project notes** shortcut when projectId passed

### 5. Page wiring

- `/research/projects/{id}`: add `ResearchGettingStarted`, `ResearchStatsPanel`, Obsidian
  export button, link to `/analytics`
- `ResearchWorkspaceShell` (Projects tab): same stats panel + getting started when project selected
- `/analytics`: add `.sav` to upload accept list; **Download for jamovi** after data loaded

### 6. Tests

- `tests/analytics/test_file_import.py`: `.sav` skipped or mocked if pyreadstat absent
- `tests/research_workspace/test_dataset_export_download.py`: jamovi zip download route

## Acceptance criteria

- [ ] Researcher can upload `.sav` on `/analytics` and see tabular data in textarea
- [ ] Researcher can download jamovi zip from `/analytics` without API knowledge
- [ ] Research project page shows PSPP install status and one-click analysis when dataset loaded
- [ ] jamovi zip downloads from research project without copying server paths
- [ ] Playbook runner shows plain-language playbook descriptions
- [ ] Obsidian vault registration uses guided copy; export button visible on project page
- [ ] No em dashes or emojis in UI copy
- [ ] Existing tests pass; new tests added for new routes

## Out of scope

- Embedding jamovi, PSPP, Obsidian, or SPSS GUIs inside Keprix
- Auto-installing PSPP on the server
- Replacing research playbooks with a new orchestration engine

## After completion

Move this file to `planning/prompts/prompts-archive/` and update
`planning/prompts/PROMPT-IMPLEMENTATION-AUDIT.md`.
