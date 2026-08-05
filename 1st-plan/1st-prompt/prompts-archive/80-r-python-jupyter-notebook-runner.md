# keprix - Prompt 80: R, Python, and Jupyter Notebook Runner

## Context

keprix needs a reproducible computation lane for research: Python, R, notebooks, statistical scripts, and analysis artifacts. This prompt extends the analytics workspace from Prompt 54.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/research_workspace/notebooks/
  __init__.py
  python_runner.py
  r_runner.py
  notebook.py
  kernel_manager.py
  sandbox.py
  artifacts.py
  html_export.py
tests/research_workspace/test_python_runner.py
tests/research_workspace/test_r_runner.py
tests/research_workspace/test_notebook_export.py
docs/research/notebook-runner.md
```

## Required Features

### Python Runner

Support:

- Pandas.
- Polars.
- DuckDB.
- Matplotlib.
- Seaborn.
- Scikit-learn if installed.
- Statsmodels if installed.

### R Runner

Support:

- Base R.
- Tidyverse if installed.
- jmv if installed.
- Survey packages if installed.
- User-approved package install instructions.

### Notebook Artifacts

Generate:

- `.ipynb` notebook.
- Python script.
- R script.
- HTML report.
- Figures.
- Tables.
- Execution log.

### Sandbox

Run code in an isolated workspace:

- No network by default.
- Explicit file allowlist.
- Runtime limit.
- Memory limit.
- Secret redaction.
- Artifact capture.

## Acceptance Criteria

- Python and R runners can be tested with fixture scripts.
- Notebook export includes code, outputs, and provenance.
- Failed cells are captured with repair suggestions.
- Dangerous code is blocked or requires approval.
- Analysis artifacts link back to dataset versions and trace IDs.

