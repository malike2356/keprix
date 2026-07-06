# Research Workspace Release Map

Dependency order for Prompts 74 through 83. Implement and verify in sequence; later prompts assume earlier modules are stable.

## Build order

| Step | Prompt | Module | API / tests |
| --- | --- | --- | --- |
| 1 | 74 | Research workspace architecture | `src/keprix/research_workspace/`, `/api/research/projects/*`, `tests/research_workspace/test_project.py` |
| 2 | 77 | Dataset and codebook manager | `research_workspace/datasets/`, `dataset_routes.py`, `tests/research_workspace/test_codebook.py` |
| 3 | 76 | Citations (Zotero / BibTeX) | `research_workspace/citations/`, `zotero_routes.py`, `tests/research_workspace/test_bibtex.py` |
| 4 | 75 | Obsidian vault adapter | `research_workspace/obsidian/`, `obsidian_routes.py`, `tests/research_workspace/test_obsidian_*.py` |
| 5 | 80 | R, Python, notebook runner | `research_workspace/notebooks/`, `notebook_routes.py`, `tests/research_workspace/test_*_runner.py` |
| 6 | 78 | PSPP CLI runner | `research_workspace/stats/pspp/`, `pspp_routes.py`, `tests/research_workspace/test_pspp_*.py` |
| 7 | 79 | jamovi export bridge | `src/keprix/analytics/jamovi/`, analytics workspace tools |
| 8 | 81 | Report generator | bibliography `report` format, notebook HTML export, graph export |
| 9 | 82 | Playbooks and UI | research playbooks UI and agent workflows (pending UI prompt) |
| 10 | 83 | Evals and release map | `evals/research/`, `tests/integration/test_research_workspace_smoke.py`, this document |

## Boundary rule

Keprix orchestrates external tools (Obsidian, Zotero, PSPP, jamovi, R, Python, Jupyter, Pandoc, Quarto). It does not replace their execution engines. See `/api/research/projects/boundary`.

## Release gate (Prompt 83)

1. `evals/research/run-research-evals.py` exits 0.
2. `tests/integration/test_research_workspace_smoke.py` passes.
3. `docs/research/reproducibility.md` documents provenance fields.
4. Reports do not ship uncited factual claims unless explicitly marked.

## Quick validation

```bash
cd keprix
.venv/bin/python evals/research/run-research-evals.py
.venv/bin/python -m pytest tests/integration/test_research_workspace_smoke.py tests/research_workspace/ -q
```

## Cross-links

- Architecture: `docs/research/research-workspace-architecture.md`
- Datasets: `docs/research/dataset-codebook-manager.md`
- Citations: `docs/research/zotero-citation-adapter.md`
- Obsidian: `docs/research/obsidian-vault-adapter.md`
- PSPP: `docs/research/pspp-runner.md`
- Notebooks: `docs/research/notebook-runner.md`
- Reproducibility: `docs/research/reproducibility.md`
