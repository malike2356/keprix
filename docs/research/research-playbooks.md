# Research playbooks

Research playbooks are YAML workflows that combine Obsidian, Zotero, datasets, statistics, notebooks, and reports inside a research project.

## Playbook catalog

| ID | Purpose |
| --- | --- |
| `literature_review` | Zotero import, claim extraction, Obsidian notes, synthesis matrix, draft review |
| `survey_analysis` | Dataset import, codebook, missing values, descriptive stats, tests, report |
| `dataset_to_report` | Dataset through notebook analysis to report draft |
| `obsidian_research_map` | Vault index, clusters, orphans, claim links, map note |
| `pspp_analysis` | Dataset prep, PSPP syntax, run, output capture, cautious interpretation |
| `jamovi_preparation` | Clean export, labels, jamovi plan, store external results |
| `borehole_field_research` | Ghana groundwater field study and operational insight report |

YAML files live in `src/keprix/research_workspace/playbooks/`.

## API

Base path: `/api/research/playbooks`

- `GET /` list playbooks
- `GET /{playbook_id}` fetch YAML spec
- `POST /{playbook_id}/run` body `{ project_id, dry_run, parameters }`
- `GET /projects/{project_id}/runs` list playbook runs for a project

Each run stores a `playbook_run` research object with `trace_id`, step artifacts, and `pending_approvals` for high-risk interpretation steps.

## CLI

```bash
cd keprix   # repository root after git clone
PYTHONPATH=src .venv/bin/python -m keprix_cli.main research list
PYTHONPATH=src .venv/bin/python -m keprix_cli.main research run rp-abc123 literature_review --dry-run
```

## UI

- `/research` workspace shell with project list
- `/research/projects/{id}` project page with sources, notes, datasets, playbook runner, timeline, and pending approvals

## Dry run

Set `dry_run: true` to execute fixture steps without writing artifacts. Live runs register traced objects and flag steps with `requires_review: true` or `risk: high`.

## Validation

```bash
cd keprix   # repository root after git clone
.venv/bin/python -m pytest tests/research_workspace/test_research_playbooks.py -q
```
