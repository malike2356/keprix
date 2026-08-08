# Keprix Prompt 158: Autonomous MCP - Architecture Reference

**Status:** Reference document. Do not archive. Read before building prompts 159-161.

---

## What this prompt pack builds

Keprix can already connect to MCP servers configured in `~/.keprix/config.yaml`. What it
cannot do:

1. Let the agent autonomously spawn an MCP when it recognises a missing capability.
2. Persist MCP connections it added during a session so they are available next time.
3. Show the user a catalog of well-known MCPs they can add with one click.
4. Let the user manage all three transport types (stdio, HTTP, SSE) with env vars from
   the web UI.
5. Enable/disable individual servers without deleting them.

Prompts 159-161 build those five capabilities in a safe, graduated order.

---

## Current state map (do not re-implement)

| File | What it does |
|---|---|
| `src/keprix/tools/mcp_tool.py` | Full MCP client runtime. Reads `mcp_servers` from `~/.keprix/config.yaml`. Supports stdio, HTTP StreamableHTTP, SSE. Thread-safe. Already has security validation, credential stripping, OAuth, reconnect backoff, sampling. |
| `src/keprix/keprix_cli/mcp_config.py` | CRUD helpers: `_get_mcp_servers()`, `_save_mcp_server()`, `_remove_mcp_server()`, `_probe_single_server()`. Reads/writes `config.yaml`. |
| `src/keprix/keprix_cli/web_server.py` lines 7205-7360 | FastAPI routes: `GET /api/mcp/servers`, `POST /api/mcp/servers`, `DELETE /api/mcp/servers/{name}`, `POST /api/mcp/servers/{name}/test`. `MCPServerCreate` model already has name/url/command/args/env/auth. |
| `frontend/src/lib/admin-api.ts` | `McpServer` type and five API functions. Type only has name/url/command/enabled/tools - missing transport field. `addMcpServer` only sends `{name, url}` - does not send command/args/env yet. |
| `frontend/src/app/(workspace)/admin/mcp/page.tsx` | Add dialog only has name+URL. No stdio form, no env editor, no capabilities viewer, no enable toggle. |
| `frontend/src/app/(workspace)/settings/page.tsx` | Settings hub card for "MCP servers" links to `/admin/mcp`. Keep that link; do not move the page. |

### What the backend can already handle but the frontend does not yet send

The backend `MCPServerCreate` already accepts:
```python
class MCPServerCreate(BaseModel):
    name: str
    url: Optional[str] = None
    command: Optional[str] = None
    args: List[str] = []
    env: Dict[str, str] = {}
    auth: Optional[str] = None
```

`GET /api/mcp/servers` already returns `transport`, `command`, `args`, and `env`
(redacted) for each server. The frontend does not yet render or send these fields.

### Missing backend endpoint

There is no `PUT /api/mcp/servers/{name}/enabled` endpoint. `admin-api.ts` calls it but
gets a 404. This must be added before the toggle in the UI can work.

---

## Design decisions

### Source of truth: config.yaml, not a new DB table

`mcp_tool.py` reads `~/.keprix/config.yaml` at session start. Adding a separate DB table
would create two sources of truth. Instead:

- `mcp_config.py` / `config.yaml` remains the single authoritative store.
- All three new features (UI upgrade, catalog, auto-spawn) write through
  `_save_mcp_server()` / `_remove_mcp_server()` exactly as the CLI does.
- The auto-spawn manager calls `_save_mcp_server()` to persist connections it adds, then
  calls `mcp_tool.register_server_runtime()` to activate them in the live session without
  requiring a restart.

`register_server_runtime()` and `unregister_server_runtime()` are the two additions
needed in `mcp_tool.py` (prompt 161). Everything else is already wired.

### MCP catalog: static Python dict, served as an API

A catalog is a curated list of well-known MCP npm packages with metadata. It does not
need a DB table. Keep it as a Python dict in a new file `mcp_catalog.py`. Serve it at
`GET /api/mcp/catalog`. The frontend reads it to show one-click add buttons.

### Auto-spawn: feature-flagged tool the agent can call explicitly

Rather than intercepting tool-not-found errors (fragile, hard to test), the agent is
given an explicit `keprix_spawn_mcp` tool it can call when it decides it needs a
capability. This is transparent, testable, and matches the way Keprix agents already
decide to use other tools.

Feature flag `KEPRIX_AUTO_MCP_SPAWN` controls whether the tool is registered at session
start:
- `false` (default): tool not available; user must add MCPs manually.
- `true`: tool is registered; agent can call it to spawn catalog entries.

Auto-spawn without credentials is safe (e.g. `filesystem`, `fetch`). Auto-spawn of MCPs
that require API keys requires the key to be in the Vault or env; if missing, the agent
is told to prompt the user.

---

## Build order

| Prompt | Title | What it adds |
|---|---|---|
| 159 | MCP Management UI Upgrade | stdio form, env vars, enable/disable backend, capabilities view, catalog browse tab |
| 160 | MCP Catalog | `mcp_catalog.py`, `GET /api/mcp/catalog`, frontend catalog tab in MCP settings |
| 161 | Autonomous MCP Spawn | `auto_mcp_spawn.py`, `keprix_spawn_mcp` tool, `register_server_runtime()` in `mcp_tool.py`, feature flag |

Build 159 first (UI improvements stand alone). Build 160 next (catalog data needed by
161 for the agent to look up entries). Build 161 last.

---

## MCP catalog entries (reference, implemented in prompt 160)

| Catalog key | npm package | Transport | Required env | Capability tags |
|---|---|---|---|---|
| `filesystem` | `@modelcontextprotocol/server-filesystem` | stdio | none | files, read, write |
| `github` | `@modelcontextprotocol/server-github` | stdio | `GITHUB_PERSONAL_ACCESS_TOKEN` | github, code, repos |
| `brave-search` | `@modelcontextprotocol/server-brave-search` | stdio | `BRAVE_API_KEY` | web, search |
| `fetch` | `@modelcontextprotocol/server-fetch` | stdio | none | web, http, scrape |
| `puppeteer` | `@modelcontextprotocol/server-puppeteer` | stdio | none | browser, automation |
| `postgres` | `@modelcontextprotocol/server-postgres` | stdio | `POSTGRES_URL` | database, sql |
| `sqlite` | `@modelcontextprotocol/server-sqlite` | stdio | none | database, sql, local |
| `slack` | `@modelcontextprotocol/server-slack` | stdio | `SLACK_BOT_TOKEN`, `SLACK_TEAM_ID` | slack, messaging |
| `google-maps` | `@modelcontextprotocol/server-google-maps` | stdio | `GOOGLE_MAPS_API_KEY` | maps, location |
| `memory` | `@modelcontextprotocol/server-memory` | stdio | none | memory, entities, knowledge |
| `sequential-thinking` | `@modelcontextprotocol/server-sequential-thinking` | stdio | none | reasoning, planning |
| `time` | `@modelcontextprotocol/server-time` | stdio | none | time, date, timezone |
| `git` | `@modelcontextprotocol/server-git` | stdio | none | git, version-control |
| `everything` | `@modelcontextprotocol/server-everything` | stdio | none | demo, test |

---

## Safety constraints (must hold across all three prompts)

1. Never auto-spawn without the `KEPRIX_AUTO_MCP_SPAWN=true` flag.
2. Never write credentials (env vars with secret values) back to the API response. The
   `_redact_mcp_env()` function in `web_server.py` already handles this; do not bypass it.
3. Security validation (`validate_mcp_server_entry` in `mcp_security.py`) runs on every
   write. The auto-spawn path must call `_save_mcp_server()` which calls this internally.
4. Stdio servers execute as local OS processes. Catalog entries are the only stdio
   servers that may be auto-spawned; arbitrary user-supplied commands are never
   auto-spawned.
5. MCPs added by the agent are tagged `"auto_spawned": true` in config so the UI can
   display an "Added automatically" badge.

---

## Acceptance gate for the full pack (after 159-161)

1. Add a GitHub MCP with a PAT via the web UI form. Reconnect Keprix. Confirm
   `mcp_github_search_repositories` appears in the tool list.
2. Disable the GitHub MCP via the toggle. Confirm the tool is no longer available
   without deleting the server config.
3. Enable `KEPRIX_AUTO_MCP_SPAWN=true`. Ask the agent "read a local file". Confirm it
   calls `keprix_spawn_mcp(catalog_name="filesystem", ...)` and the filesystem tools
   appear without the user touching the settings page.
4. Navigate to `/admin/mcp`. Confirm the GitHub entry shows "Added manually" and the
   filesystem entry shows "Added automatically".
5. Delete both MCPs via the UI. Confirm config.yaml no longer contains them.
