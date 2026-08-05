# Graphiti bridge

The Graphiti bridge connects Keprix to a Graphiti MCP-compatible server, or to a built-in local episodic store when `GRAPHITI_MCP_URL` is empty / `builtin`.

## Configuration

```bash
# Built-in local store (default when unset)
GRAPHITI_MCP_URL=
KEPRIX_GRAPHITI_ENABLED=1

# Or point at an external Graphiti MCP (docker network example):
# GRAPHITI_MCP_URL=http://keprix-graphiti-mcp:8000/mcp
```

The optional MCP catalog entry is `src/keprix/optional-mcps/graphiti/manifest.yaml`.
The local store writes under `{KEPRIX_HOME}/brain/graphiti/local/`.

Local MCP helper: `keprix/docker/graphiti/README.md` (health `http://127.0.0.1:8000/health`).

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/brain/graphiti/status` | Connection health: `connected`, `misconfigured`, `unreachable`, or `disabled` |
| `POST` | `/api/brain/graphiti/ingest` | Ingest `research`, `session`, `vault_file`, or `manual` content |
| `GET` | `/api/brain/graphiti/jobs` | List ingest jobs |
| `GET` | `/api/brain/graphiti/jobs/{id}` | Job detail |
| `POST` | `/api/brain/graphiti/query` | Query debugger |

Jobs are stored under `{KEPRIX_HOME}/brain/graphiti/jobs/`.

## Tool

Enable the `brain` toolset to expose `graphiti_query`:

```json
{
  "query": "What did we learn about competitor X?",
  "max_results": 10,
  "include_sources": true
}
```

When Graphiti is unavailable, the tool returns a structured error with `fallback: native brain search` rather than blocking the agent run.
