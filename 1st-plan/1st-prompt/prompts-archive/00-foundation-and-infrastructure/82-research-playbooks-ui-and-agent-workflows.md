# keprix - Prompt 82: Research Playbooks, UI, and Agent Workflows

## Context

The Research Workspace should be usable through playbooks, UI, CLI, and chat. This prompt adds end-to-end workflows that combine Obsidian, Zotero, datasets, statistics, notebooks, and reports.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/research_workspace/playbooks/
  literature_review.yaml
  survey_analysis.yaml
  dataset_to_report.yaml
  obsidian_research_map.yaml
  pspp_analysis.yaml
  jamovi_preparation.yaml
  abbis_borehole_research.yaml
cli/commands/research.py
frontend/src/app/research/projects/[id]/page.tsx
frontend/src/components/research/ResearchPlaybookRunner.tsx
frontend/src/components/research/ResearchTimeline.tsx
tests/research_workspace/test_research_playbooks.py
docs/research/research-playbooks.md
```

## Required Playbooks

### Literature Review

Steps:

- Import Zotero collection.
- Summarize selected papers.
- Extract claims.
- Create Obsidian literature notes.
- Build synthesis matrix.
- Draft literature review.

### Survey Analysis

Steps:

- Import dataset.
- Create codebook.
- Validate missing values.
- Generate descriptive statistics.
- Run selected statistical tests.
- Generate report.

### Obsidian Research Map

Steps:

- Index vault.
- Identify note clusters.
- Find orphan notes.
- Link sources to claims.
- Generate research map note.

### PSPP Analysis

Steps:

- Prepare dataset and codebook.
- Generate PSPP syntax.
- Run PSPP if available.
- Capture outputs.
- Interpret results cautiously.

### jamovi Preparation

Steps:

- Prepare clean dataset.
- Export labels and missing-value notes.
- Generate jamovi analysis plan.
- Store user-provided results and R syntax.

### AbbiS Borehole Research

Steps:

- Collect borehole domain sources.
- Build Ghana groundwater notes.
- Build dataset and codebook.
- Analyze field data.
- Generate operational insight report.

## UI Requirements

Research project page should show:

- Sources.
- Notes.
- Datasets.
- Analyses.
- Reports.
- Evidence map.
- Playbook runs.
- Pending approvals.

## Acceptance Criteria

- Each playbook can run against fixtures or dry-run mode.
- UI exposes research projects and playbook runs.
- CLI can start a research playbook.
- All outputs become artifacts with trace IDs.
- High-risk analysis claims are marked as needing human review.

