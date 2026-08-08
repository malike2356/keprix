# keprix - Prompt 83: Research Evals, Reproducibility, and Release Map

## Context

Research features can cause subtle harm if citations are wrong, statistics are misreported, or generated reports invent claims. This prompt adds evals, reproducibility checks, and the final release map for the Research Workspace.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
evals/research/
  README.md
  citation-fixtures.json
  dataset-fixtures.json
  pspp-fixtures.json
  report-fixtures.json
  scoring-rubric.md
  run-research-evals.py
docs/research/reproducibility.md
docs/research/research-workspace-release-map.md
tests/integration/test_research_workspace_smoke.py
```

## Eval Categories

Test:

- Citation accuracy.
- Source attribution.
- Claim-to-evidence linking.
- Dataset import correctness.
- Codebook preservation.
- PSPP syntax generation.
- Statistical result preservation.
- Report bibliography generation.
- Obsidian note safety.
- Reproducibility bundle export.

## Reproducibility Rules

Every research output must record:

- Input sources.
- Dataset version.
- Codebook version.
- Analysis script.
- Tool version where available.
- Model used.
- Prompt version.
- Trace ID.
- Human review status.

## Smoke Test

Create an integration smoke test that:

1. Creates a research project.
2. Imports one source.
3. Imports one Zotero or BibTeX fixture.
4. Creates one Obsidian-style note.
5. Imports one dataset.
6. Generates a codebook.
7. Generates PSPP syntax.
8. Runs a mocked statistical output.
9. Generates a report.
10. Exports an evidence bundle.

## Release Map

Document dependency order:

1. Prompt 74 architecture.
2. Prompt 77 dataset and codebook manager.
3. Prompt 76 citations.
4. Prompt 75 Obsidian adapter.
5. Prompt 80 R, Python, and notebook runner.
6. Prompt 78 PSPP runner.
7. Prompt 79 jamovi bridge.
8. Prompt 81 report generator.
9. Prompt 82 playbooks and UI.
10. Prompt 83 evals and release map.

## Acceptance Criteria

- Research eval runner exists.
- Integration smoke test covers the main workflow.
- Reproducibility docs are clear.
- Release map links prompts 74 through 83.
- Research reports never ship uncited factual claims unless explicitly marked as generated opinion or analysis.
