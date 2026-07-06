# Research Workspace Reproducibility

Every research output in Keprix must be traceable from claim to source, dataset, analysis, and export.

## Required provenance fields

Record these on each research object (`src/keprix/research_workspace/schemas.py`):

| Field | Description |
| --- | --- |
| Input sources | Registered `source` rows and citation imports |
| Dataset version | `dataset_id` and `version_id` from `DatasetManager` |
| Codebook version | Codebook JSON stored under workspace `datasets/codebooks/` |
| Analysis script | PSPP syntax, notebook path, or R/Python runner artifact |
| Tool version | PSPP `--version`, Python/R detection where available |
| Model used | LLM or embedding model for generated summaries (when applicable) |
| Prompt version | Playbook or agent prompt identifier |
| Trace ID | `new_trace_id()` on every saved object |
| Human review status | `approved` flag on claims and export policy on objects |

## Storage locations

- Projects, sources, claims, bundles: workspace data plane SQLite (`ResearchWorkspaceStore`)
- Datasets and codebooks: `{workspace}/datasets/`
- Citations cache: `{workspace}/citations/{project_id}.json`
- Lineage steps: `{workspace}/datasets/lineage/`
- Evidence bundles: `research_objects` with `object_type=evidence_bundle`

## Reproducibility bundle export

Use `EvidenceService.build_bundle()` to collect traced members (sources, claims, datasets, reports). Lineage is retrieved with `trace_lineage(project_id, object_id)`.

## Report safety rule

Factual claims in generated reports must cite a registered source or carry an explicit marker such as `[analysis]`, `[generated opinion]`, or `[hypothesis]`. The eval runner enforces this via `validate_report_claims()` in `evals/research/run-research-evals.py`.

## Verification

```bash
cd keprix
.venv/bin/python evals/research/run-research-evals.py
.venv/bin/python -m pytest tests/integration/test_research_workspace_smoke.py -v
```

## Related docs

- `docs/research/research-workspace-architecture.md` (Prompt 74)
- `docs/research/dataset-codebook-manager.md` (Prompt 77)
- `docs/research/research-workspace-release-map.md` (Prompt 83)
