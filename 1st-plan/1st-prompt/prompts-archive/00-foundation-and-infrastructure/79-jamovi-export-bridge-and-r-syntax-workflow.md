# keprix - Prompt 79: jamovi Export Bridge and R Syntax Workflow

## Context

jamovi is a GUI-first statistical spreadsheet backed by R workflows. keprix should support jamovi through clean file exchange, analysis planning, R syntax capture, and module-aware documentation. Direct GUI automation is not the first integration path.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/research_workspace/stats/jamovi/
  __init__.py
  export_bridge.py
  import_bridge.py
  analysis_plan.py
  r_syntax.py
  module_catalog.py
  metadata.py
tests/research_workspace/test_jamovi_export_bridge.py
tests/research_workspace/test_jamovi_analysis_plan.py
tests/research_workspace/test_jamovi_r_syntax.py
docs/research/jamovi-bridge.md
```

## Required Features

### Export Bridge

Prepare jamovi-ready packages:

- Clean CSV.
- Variable labels.
- Value labels.
- Missing-value notes.
- Measurement levels.
- Suggested analyses.
- Instructions for import.

### Analysis Plan

Generate human-readable analysis plans for jamovi:

- Which variables to load.
- Which analysis to run.
- Which assumptions to check.
- Which plots to generate.
- How to interpret outputs.

### R Syntax Workflow

Support:

- Capturing R syntax from jamovi outputs when user provides it.
- Converting keprix analysis plan to equivalent R script where practical.
- Storing R syntax as reproducible artifact.

### Module Catalog

Maintain an optional catalog of jamovi modules and use cases:

- Regression.
- ANOVA.
- Mediation.
- Reliability.
- Psychometrics.
- Meta-analysis.
- Power analysis.
- Survival analysis.

Do not install modules automatically without user approval.

## Acceptance Criteria

- keprix can prepare a dataset package for jamovi.
- keprix can generate an analysis plan a non-technical user can follow in jamovi.
- User-provided R syntax can be stored and linked to the analysis run.
- jamovi remains an external tool; keprix does not pretend to control it directly.
- Tests cover export package generation and analysis plan output.

