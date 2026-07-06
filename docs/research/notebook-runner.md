# Notebook runner

The research notebook lane runs Python and R analysis scripts in an isolated workspace, captures artifacts, and links results to dataset versions and trace IDs.

## Components

| Module | Role |
|--------|------|
| `kernel_manager.py` | Detect Python/R binaries and optional packages |
| `sandbox.py` | Dangerous-code scan, secret redaction, path allowlist, repair hints |
| `python_runner.py` | Execute `.py` scripts with timeout and logging |
| `r_runner.py` | Execute `.R` scripts with timeout and logging |
| `notebook.py` | Build `.ipynb` documents with provenance metadata |
| `artifacts.py` | Collect figures, tables, logs, and persist run bundles |
| `html_export.py` | Render HTML reports from notebook JSON |
| `runner.py` | Prepare and execute runs; store research objects |

## API

Base path: `/api/research/notebooks`

- `GET /status` - Python and R runtime detection
- `POST /prepare` - Create run workspace, script, and `.ipynb` with provenance
- `POST /execute` - Run prepared script and emit HTML, logs, and artifacts

### Prepare body

```json
{
  "project_id": "proj-123",
  "runtime": "python",
  "code": "print('hello')",
  "dataset_id": "ds-abc",
  "approve_dangerous": false,
  "allow_network": false,
  "timeout_seconds": 60
}
```

### Execute body

```json
{
  "run_id": "nb-deadbeef",
  "approve_dangerous": false,
  "timeout_seconds": 60
}
```

## Sandbox policy

- Network calls (`requests`, `urllib`, sockets) are blocked unless `allow_network` is true.
- Dangerous primitives (`eval`, `exec`, `subprocess`, `os.system`) require `approve_dangerous`.
- Scripts run in a per-run directory under `notebook_runs/`.
- Dataset files are copied into the run directory when `dataset_id` is provided.
- Secrets in stdout/stderr are redacted in `execution.log`.
- Failed runs include `repair_suggestions` in the notebook error output.

## Artifacts

Each completed run may produce:

- `notebook.ipynb`
- `analysis.py` or `analysis.R`
- `analysis_export.py` (Python reruns)
- `report.html`
- `execution.log`
- Figures (`*.png`) and tables (`*.csv`) written by the script

Artifacts are copied to `notebook_runs/artifacts/{run_id}/` and registered as `notebook_run` research objects with `trace_id`, `dataset_id`, and `dataset_version`.

## Optional packages

Python: pandas, polars, duckdb, matplotlib, seaborn, scikit-learn, statsmodels (detected when installed).

R: tidyverse, jmv, survey (detected when installed). Additional packages require manual install with user approval outside the sandbox.

## Local validation

```bash
cd /opt/lampp/htdocs/verlox/keprix
.venv/bin/python -m pytest tests/research_workspace/test_python_runner.py \
  tests/research_workspace/test_r_runner.py \
  tests/research_workspace/test_notebook_export.py -q
```
