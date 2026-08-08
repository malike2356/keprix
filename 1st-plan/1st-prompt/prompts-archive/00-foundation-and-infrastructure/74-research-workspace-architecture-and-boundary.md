# keprix - Prompt 74: Research Workspace Architecture and Boundary

> **Status (2026-07-05):** Implemented `src/keprix/research_workspace/` (projects, sources, evidence, artifacts, workflow adapters, permissions), data plane v2 migration, `/api/research/projects/*`, `/research` UI shell with Deep Research tab, `docs/research/research-workspace-architecture.md`, and 7 tests.

## Context

keprix should support academic research, market research, NGO field studies, survey analysis, policy reports, AbbiS borehole research, and business intelligence. It should not replace Obsidian, Zotero, PSPP, jamovi, R, Python, Jupyter, Pandoc, or Quarto. keprix should orchestrate them through files, APIs, CLI tools, adapters, and reproducible playbooks.

This prompt defines the Research Workspace as a product surface and integration boundary.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Related Prompts

Read first:

```text
planning/prompts/40-combined-data-ml-research-workspace-architecture.md
planning/prompts/54-taskweaver-style-data-analytics-code-workspace.md
planning/prompts/101-llamaindex-style-document-agents-indexing-and-rag-pipelines.md
planning/prompts/104-haystack-style-production-rag-pipelines-and-routing.md
planning/prompts/69-llamaindex-style-document-agents-indexing-and-rag-pipelines.md
planning/prompts/72-haystack-style-production-rag-pipelines-and-routing.md
```

## Files To Create

```text
backend/research_workspace/
  __init__.py
  project.py
  source.py
  evidence.py
  artifact.py
  workflow.py
  permissions.py
  schemas.py
  errors.py
backend/api/research_workspace.py
frontend/src/app/research/page.tsx
frontend/src/components/research/ResearchProjectList.tsx
frontend/src/components/research/ResearchWorkspaceShell.tsx
tests/research_workspace/test_project.py
tests/research_workspace/test_evidence.py
tests/research_workspace/test_permissions.py
docs/research/research-workspace-architecture.md
```

## Core Product Model

Create first-class objects:

- Research project.
- Source.
- Citation.
- Note.
- Claim.
- Dataset.
- Codebook.
- Analysis run.
- Statistical output.
- Figure.
- Report.
- Evidence bundle.

Each object must include:

- Workspace ID.
- Project ID.
- Owner.
- Source path or URI.
- Provenance.
- Created and updated timestamps.
- Trace ID.
- Sensitivity level.
- Export policy.

## Integration Boundary

keprix owns:

- Project orchestration.
- Source ingestion.
- Evidence tracking.
- Agent analysis.
- Playbook execution.
- Artifact store.
- Report assembly.
- Audit trail.

External tools own:

- Obsidian visual note editing and graph UX.
- Zotero library management.
- PSPP statistical engine.
- jamovi GUI statistical spreadsheet.
- R and Python package ecosystems.
- Jupyter notebook editing where users prefer notebooks.
- Pandoc and Quarto rendering engines.

## Acceptance Criteria

- Research Workspace has a documented data model.
- UI has a Research entry point and project shell.
- Every research artifact can be traced back to source material or a generated run.
- The architecture explicitly avoids replacing external specialist tools.
- Existing analytics, RAG, and document-agent prompts are referenced rather than duplicated.
