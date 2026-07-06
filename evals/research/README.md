# Research Workspace Evals

Eval harness for Prompt 83: citation accuracy, dataset/codebook integrity, PSPP syntax, report safety, and reproducibility bundles.

## Run

From the `keprix/` project root:

```bash
.venv/bin/python evals/research/run-research-evals.py
```

## Fixtures

| File | Purpose |
| --- | --- |
| `citation-fixtures.json` | BibTeX / Better BibTeX parsing and bibliography export |
| `dataset-fixtures.json` | CSV import and codebook variable expectations |
| `pspp-fixtures.json` | PSPP syntax fragments and mocked statistical output |
| `report-fixtures.json` | Cited vs uncited claim checks and Obsidian unsafe patterns |

## Related tests

```bash
.venv/bin/python -m pytest tests/integration/test_research_workspace_smoke.py -v
.venv/bin/python -m pytest tests/research_workspace/ -q
```

## Docs

- `docs/research/reproducibility.md`
- `docs/research/research-workspace-release-map.md`
