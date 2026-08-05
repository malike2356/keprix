# Keprix Prompt 185: Agent Apps - Observability, Run History, and Evals UI

## Purpose

Persist traces and run history (not in-memory only), surface in app detail and `/agent-runtime`,
and run bundled eval suites from UI. Required for support, compliance, and sellable SLAs.

Read reference **177**. Requires **180** (lifecycle events). Align with prompt **57** (evals).

---

## Dependencies

- `src/keprix/agent_apps/lifecycle.py` (`_global_traces`)
- `frontend/src/app/(workspace)/agent-runtime/page.tsx`
- `frontend/src/app/(workspace)/evals/page.tsx`
- `src/keprix/agent_apps/eval_runner.py`

---

## What to build

### 1. Persistent run store

```text
src/keprix/agent_apps/run_store.py
```

SQLite at `~/.keprix/agent_apps/runs.db`:

```sql
runs(
  trace_id TEXT PRIMARY KEY,
  app_name TEXT,
  user_id TEXT,
  status TEXT,           -- running | success | error
  runner TEXT,
  input_json TEXT,
  output_json TEXT,
  error TEXT,
  started_at TEXT,
  finished_at TEXT,
  duration_ms INTEGER
)

lifecycle_events(
  id INTEGER PRIMARY KEY,
  trace_id TEXT,
  event TEXT,
  payload_json TEXT,
  created_at TEXT
)
```

On each run: write run row + append events. Keep in-memory cache optional for dev.

### 2. API

```python
GET /api/agent-apps/{name}/runs?limit=20&offset=0
GET /api/agent-apps/runs/{trace_id}
GET /api/agent-apps/runs/{trace_id}/events
```

List response: summary cards (status, duration, started_at, input preview).

### 3. Wire lifecycle

Replace or supplement `_global_traces` append with `run_store.record_event(...)`.
`get_run_traces` reads from DB when trace_id provided.

### 4. App detail: History tab

On `/agent-apps/[slug]`:

- Tab **Run** | **History** | **Evals**
- History: table with status chip, time ago, duration, **View** opens drawer with events timeline
- Re-run button prefills last inputs

### 5. Agent runtime integration

Filter `/agent-runtime` (or API behind it) by `source=agent_app` and `app_name`.
Link from history row: "Open in Agent Runtime".

If agent-runtime API lacks filter, add query param `?source=agent_app&app=daily-standup`.

### 6. Evals UI

```python
POST /api/agent-apps/{name}/evals/run   # existing eval_runner
GET  /api/agent-apps/{name}/evals/last
```

App detail **Evals** tab:

- Show last run score / pass-fail
- **Run eval suite** button (admin or app owner)
- Link to global `/evals` filtered by suite name

### 7. Retention

Config `KEPRIX_AGENT_APP_RUN_RETENTION_DAYS` (default 30). Nightly prune job or prune on insert.

---

## Acceptance criteria

- [ ] Runs survive API restart.
- [ ] History tab shows last 20 runs per app.
- [ ] Trace drawer shows lifecycle events in order.
- [ ] Eval run from UI displays results.
- [ ] Agent runtime filter shows agent app runs.
- [ ] Tests: run_store CRUD, API list/detail.

---

## Out of scope

- Full distributed tracing / OpenTelemetry export
- Customer-facing audit PDF export

---

## Archive

On completion: move to `prompts-archive/`.
