# keprix - Prompt 81: Report Generator, Pandoc, Quarto, and Evidence Bundles

## Context

Research workflows end in documents: reports, briefs, papers, policy notes, client deliverables, and evidence bundles. keprix should assemble cited, reproducible reports from notes, datasets, statistical outputs, charts, and sources.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/`

Python package root: `src/keprix/`

## MVP Slice (implemented)

- Markdown report renderer with bibliography and evidence map.
- Playbook handlers for `report.generate`, `report.draft_literature_review`, and `report.operational_insight`.
- Pandoc adapter with graceful missing-tool fallback.
- Enhanced evidence bundle export package (JSON manifest).
- REST API for report generation and evidence export.

Deferred in this slice:

- Frontend UI (`ReportBuilder.tsx`, `EvidenceBundlePanel.tsx`).
- Full Quarto project export (stub only).
- Figure/script/table packaging into zip archives (see extension plan below).

## Files

```text
src/keprix/research_workspace/reports/
  __init__.py
  schemas.py
  report.py
  outline.py
  renderer.py
  pandoc.py
  quarto.py              # stub / deferred
  bibliography.py        # wraps citations/bibliography.py
  evidence_bundle.py
  templates.py
tests/research_workspace/
  test_report_outline.py
  test_report_renderer.py
  test_evidence_bundle.py
```

Deferred files:

```text
frontend/src/components/research/ReportBuilder.tsx
frontend/src/components/research/EvidenceBundlePanel.tsx
docs/research/report-generator.md
```

## Reuse (do not duplicate)

| Need | Reuse |
| --- | --- |
| Bibliography rendering | `src/keprix/research_workspace/citations/bibliography.py` via `reports/bibliography.py` |
| Citation records | `src/keprix/research_workspace/citations/registry.py` (`CitationLibrary`) |
| Evidence bundles | `src/keprix/research_workspace/evidence.py` (`EvidenceService.build_bundle`) |
| Playbook wiring | `src/keprix/research_workspace/playbook_runner.py` (`HANDLERS`) |
| Fixtures | `evals/research/report-fixtures.json`, `citation-fixtures.json` |

## Report Types

Support:

- Literature review.
- Methods and results report.
- Survey analysis report.
- Market research report.
- Policy brief.
- AbbiS borehole research report.
- Evidence appendix.
- Client-ready PDF.

## Inputs

Use:

- Obsidian notes.
- Zotero citations.
- Dataset codebook.
- PSPP outputs.
- R or Python outputs.
- Figures.
- Claims.
- Source excerpts.
- Human-reviewed findings.

## Renderers

Support:

- Markdown (default, always available).
- HTML through Pandoc where installed.
- PDF through Pandoc where installed.
- DOCX through Pandoc where installed.
- Quarto project export where installed (deferred stub).

If Pandoc or Quarto is missing, produce Markdown and setup instructions.

## Evidence Bundle

Every report can export:

- Source list.
- Citation list.
- Dataset versions.
- Analysis scripts (extension).
- Output tables (extension).
- Figures (extension).
- Claim-to-evidence map.
- Trace log.

Current MVP exports a JSON manifest via `POST /api/research/projects/{id}/evidence-bundles/export`.

## API

```text
POST /api/research/projects/{project_id}/reports/generate
POST /api/research/projects/{project_id}/evidence-bundles/export
```

Existing bundle creation remains at:

```text
POST /api/research/projects/{project_id}/evidence-bundles
```

## Playbook Actions

| Action | Default report type |
| --- | --- |
| `report.generate` | `survey_analysis` |
| `report.draft_literature_review` | `literature_review` |
| `report.operational_insight` | `abbis_borehole` |

Override via playbook run `parameters.report_type`.

## Evidence Extension Plan

Phase 2 (not in MVP):

1. Zip export under `workspace/reports/{project_id}/bundles/` with `manifest.json`, `report.md`, `bibliography.bib`, and copied artifact files.
2. Link analysis runs (`analysis_run` objects) and notebook HTML outputs into the bundle manifest.
3. Add figure/table collectors from `stats/` and `notebooks/` artifact payloads.
4. Wire Quarto adapter to emit `.qmd` plus `quarto render` when installed.
5. Add frontend report builder and evidence panel for human review before export.

## Acceptance Criteria

- keprix can generate a Markdown report with citations and evidence links.
- Pandoc and Quarto are optional adapters with graceful missing-tool behavior.
- Evidence bundle links every major claim to source or analysis artifact.
- Reports preserve citation keys and bibliography.
- Playbook `report.*` steps produce `report` artifacts (unblocks Prompt 82 playbooks).
- Tests cover outline, rendering, bibliography, evidence bundle generation, API, and playbook wiring.

## Validation

```bash
cd /opt/lampp/htdocs/verlox/keprix
PYTHONPATH=src pytest tests/research_workspace/test_report_outline.py \
  tests/research_workspace/test_report_renderer.py \
  tests/research_workspace/test_evidence_bundle.py -q
```
