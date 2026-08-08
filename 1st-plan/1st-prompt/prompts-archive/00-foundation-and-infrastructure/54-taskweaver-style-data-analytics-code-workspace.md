# keprix - Prompt 54: TaskWeaver-Style Data Analytics and Code Workspace

> **Status (2026-07-05):** Returned from `completed/` to `pending-prompts/`. `analytics_routes.py` unwired; Jamovi bridge returns stub error. Wire on `src/keprix/api/server.py` before re-archiving.

## Context

Adopt TaskWeaver's strongest ideas into keprix: code-first analytics, stateful execution, DataFrame memory, plugin execution, reflective repair, code verification, and container isolation.

This makes keprix useful for machine learning, data analytics, deep research, SPSS/PSPP/Jamovi-style analysis, dashboards, business reporting, and local research workflows.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/taskweaver/README.md
planning/agents-to-adopt/taskweaver/taskweaver/planner
planning/agents-to-adopt/taskweaver/taskweaver/code_interpreter
planning/agents-to-adopt/taskweaver/taskweaver/plugin
planning/agents-to-adopt/taskweaver/project/plugins
```

## Files To Create

```text
backend/analytics/
  __init__.py
  planner.py
  code_interpreter.py
  code_verifier.py
  dataframe_memory.py
  reflective_execution.py
  plugin_runner.py
  container_executor.py
  experience_store.py
  notebooks.py
  reports.py
  statistical_methods.py
tests/analytics/test_code_interpreter.py
tests/analytics/test_dataframe_memory.py
tests/analytics/test_plugin_runner.py
tests/analytics/test_code_verifier.py
```

## Required Features

### Code-First Planning

Convert analytics requests into:

- Plan.
- Data needed.
- Code cells.
- Expected outputs.
- Verification checks.
- Report structure.

### Stateful Execution

Persist:

- Chat history.
- Code history.
- Variables metadata.
- DataFrame schemas.
- Generated charts.
- Output files.

Do not serialize raw sensitive data into logs.

### Container Execution

Run generated code in isolated containers by default.

Support:

- Python.
- R if available.
- PSPP command line if available.
- Jamovi export/import stubs if available.

### Code Verification

Before execution:

- Block filesystem escape.
- Block network by default unless approved.
- Block credential access.
- Block shell execution unless approved.
- Check imports against allowlist.
- Estimate runtime and memory.

### Reflective Execution

If code fails:

- Capture error.
- Ask model for fix.
- Re-run within retry limit.
- Keep full revision trail.

## Plugins To Add

Implement or stub with clear setup instructions:

- `sql_pull_data`
- `anomaly_detection`
- `paper_summary`
- `speech2text`
- `text2speech`
- `image2text`
- `text_classification`
- `product_search`

Do not add joke/demo plugins.

## UI/API

Add analytics workspace endpoints:

```text
POST /api/analytics/sessions
POST /api/analytics/{session_id}/run
GET /api/analytics/{session_id}
GET /api/analytics/{session_id}/artifacts
POST /api/analytics/{session_id}/approve
```

## Acceptance Criteria

- User can upload or connect data and ask for analysis.
- keprix generates verified code before execution.
- DataFrame schemas persist between turns.
- Failed code can be repaired reflectively.
- Container isolation is default.
- Generated reports cite data sources and methods.
- Tests cover code safety, DataFrame memory, plugin execution, and failed-code repair.

