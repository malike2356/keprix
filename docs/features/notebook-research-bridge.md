# Notebook Research Bridge

The notebook research bridge adds a source-grounded research tier to `/research`.

## Modes

- **Quick Notebook** runs fully inside Keprix. Paste or upload sources, ask a question, and Keprix produces a deterministic Markdown report with inline source markers.
- **External** is hidden unless an operator configures `NOTEBOOKLM_BRIDGE_CMD` or `NOTEBOOKLM_MCP_URL`. If the external bridge is requested but unavailable, Keprix falls back to Quick Notebook.

## API

- `POST /api/research/notebook/sources` normalizes a source.
- `POST /api/research/notebook` creates a notebook research job.
- `GET /api/research/notebook` lists persisted jobs.
- `GET /api/research/notebook/{job_id}` returns status, report, sources, and citations.
- `POST /api/research/notebook/{job_id}/export` writes Markdown to disk.

Jobs are stored under `{KEPRIX_HOME}/research/notebook/{job_id}.json`; exports default to `{KEPRIX_HOME}/research/notebook/exports/{job_id}.md`.

## Configuration

```yaml
notebook_research:
  enabled: true
  native_max_sources: 20
  external:
    enabled: false
    command: ""
    mcp_url: ""
```

Optional environment variables:

- `KEPRIX_NOTEBOOK_RESEARCH_ENABLED`
- `NOTEBOOKLM_BRIDGE_CMD`
- `NOTEBOOKLM_MCP_URL`

The optional MCP catalog entry is `src/keprix/optional-mcps/notebooklm/manifest.yaml`.
