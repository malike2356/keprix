# keprix - Prompt 78: PSPP CLI Runner and SPSS Syntax Generator

> **Status (2026-07-05):** Implemented `src/keprix/research_workspace/stats/pspp/` (syntax generator, sandboxed runner, output parser), `/api/research/pspp/*`, integrated dataset PSPP export, `docs/research/pspp-runner.md`, and 7 new tests (43 total in `tests/research_workspace/`).

## Context

PSPP gives keprix an open SPSS-compatible statistical workflow. keprix should generate PSPP syntax, run the PSPP command-line engine where installed, capture outputs, and store reproducible analysis artifacts.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/research_workspace/stats/pspp/
  __init__.py
  syntax.py
  runner.py
  output_parser.py
  procedures.py
  templates.py
  errors.py
tests/research_workspace/test_pspp_syntax.py
tests/research_workspace/test_pspp_runner.py
tests/research_workspace/test_pspp_output_parser.py
docs/research/pspp-runner.md
```

## Required Features

### Syntax Generator

Generate `.sps` syntax for:

- DATA LIST.
- GET DATA.
- VARIABLE LABELS.
- VALUE LABELS.
- MISSING VALUES.
- FREQUENCIES.
- DESCRIPTIVES.
- CROSSTABS.
- T-TEST.
- ONEWAY.
- CORRELATIONS.
- REGRESSION.
- LOGISTIC REGRESSION where available.

### Runner

Run:

```text
pspp analysis.sps -o output.html
pspp analysis.sps -o output.odt
pspp analysis.sps -o output.txt
```

Detect whether PSPP is installed. If not installed, return setup instructions and keep the generated syntax artifact.

### Output Artifacts

Store:

- Syntax file.
- Dataset version.
- PSPP output.
- Parsed tables where possible.
- Trace ID.
- Warnings and errors.

## Safety Rules

- Run PSPP in a sandboxed working directory.
- Do not allow arbitrary shell fragments in generated syntax.
- Require approval before reading external paths.
- Preserve original datasets.

## Acceptance Criteria

- keprix can generate PSPP syntax from a dataset and codebook.
- Runner gracefully handles PSPP not installed.
- Output files are stored as research artifacts.
- Basic output tables can be parsed or linked.
- Tests cover syntax generation and runner behavior.
