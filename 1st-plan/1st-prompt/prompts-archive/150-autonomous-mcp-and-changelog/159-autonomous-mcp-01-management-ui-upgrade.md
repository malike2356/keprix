# Keprix Prompt 159: Autonomous MCP - Management UI Upgrade

## Purpose

The existing `/admin/mcp` page only lets the user add MCP servers by URL. The backend
already supports stdio (command + args + env) but the frontend never sends those fields.
This prompt closes that gap and adds the missing `PUT .../enabled` backend endpoint so
the enable/disable toggle actually works.

After this prompt:
- Users can add stdio MCP servers (command, args, env key-value pairs) from the UI.
- Users can edit an existing server (change command/URL, add/remove env vars).
- The enable/disable toggle persists correctly.
- Each server row shows its transport type and which tools it exposes (after "Test
  connection" or at load time if already probed).
- Servers added by the agent display an "Auto-added" badge.

---

## Dependencies

- Reference: `../prompts-archive/ref-158-autonomous-mcp-00-architecture-reference.md` (read first).
- `src/keprix/keprix_cli/mcp_config.py` - `_get_mcp_servers`, `_save_mcp_server`,
  `_remove_mcp_server`.
- `src/keprix/keprix_cli/web_server.py` - existing MCP routes at lines ~7205-7360.
- `frontend/src/lib/admin-api.ts` - `McpServer` type and API functions.
- `frontend/src/app/(workspace)/admin/mcp/page.tsx` - page to upgrade.

---

## What to build

### 1. Backend: `PUT /api/mcp/servers/{name}/enabled` endpoint

Add this to `web_server.py` after the existing `DELETE /api/mcp/servers/{name}` route.

```python
class MCPServerEnabledBody(BaseModel):
    enabled: bool


@app.put("/api/mcp/servers/{name}/enabled")
async def set_mcp_server_enabled(
    name: str,
    body: MCPServerEnabledBody,
    profile: Optional[str] = None,
):
    from keprix_cli.mcp_config import _get_mcp_servers, _save_mcp_config

    with _profile_scope(profile):
        servers = _get_mcp_servers()
    if name not in servers:
        raise HTTPException(status_code=404, detail=f"Server '{name}' not found")

    servers[name]["enabled"] = body.enabled

    with _profile_scope(profile):
        _save_mcp_config({"mcp_servers": servers})

    return {"ok": True, "name": name, "enabled": body.enabled}
```

Check `mcp_config.py` for how `_save_mcp_config` works (it may be named differently).
The pattern is: load the full config dict, update the `mcp_servers` key, call
`save_config(config)`. Follow whatever the existing save helper does exactly.

### 2. Backend: `PUT /api/mcp/servers/{name}` endpoint (edit existing)

Add this after the enabled endpoint:

```python
@app.put("/api/mcp/servers/{name}")
async def update_mcp_server(
    name: str,
    body: MCPServerCreate,
    profile: Optional[str] = None,
):
    from keprix_cli.mcp_config import _get_mcp_servers, _save_mcp_server, _remove_mcp_server

    with _profile_scope(profile):
        servers = _get_mcp_servers()
    if name not in servers:
        raise HTTPException(status_code=404, detail=f"Server '{name}' not found")

    # Build new config from body, preserving auto_spawned flag
    existing = servers[name]
    server_config: Dict[str, Any] = {}
    if body.url:
        server_config["url"] = body.url.strip()
    if body.command:
        server_config["command"] = body.command.strip()
        if body.args:
            server_config["args"] = list(body.args)
    if body.env:
        server_config["env"] = dict(body.env)
    if body.auth:
        server_config["auth"] = body.auth
    # Preserve auto_spawned and enabled flags from existing config
    for flag in ("auto_spawned", "enabled"):
        if flag in existing:
            server_config[flag] = existing[flag]

    new_name = (body.name or name).strip()
    with _profile_scope(body.profile or profile):
        if new_name != name:
            _remove_mcp_server(name)
        if not _save_mcp_server(new_name, server_config):
            raise HTTPException(
                status_code=400,
                detail=f"Server '{new_name}' rejected: suspicious configuration",
            )

    return _mcp_server_summary(new_name, server_config)
```

### 3. `frontend/src/lib/admin-api.ts` - extend McpServer type and add functions

Replace the existing `McpServer` type and MCP functions with the following. Do NOT
remove any existing exports that are unrelated to MCP.

```typescript
export type McpServer = {
  name: string;
  transport: "stdio" | "http" | "sse" | "unknown";
  url?: string | null;
  command?: string | null;
  args?: string[];
  env?: Record<string, string>;
  auth?: string | null;
  enabled: boolean;
  tools?: string[] | null;
  auto_spawned?: boolean;
};

export type McpServerInput = {
  name: string;
  url?: string;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  auth?: string;
};

export async function fetchMcpServers(): Promise<McpServer[]> {
  const data = await parseJson<{ servers: McpServer[] }>(
    await ceApi("/api/mcp/servers"),
    "Failed to load MCP servers",
  );
  return data.servers;
}

export async function addMcpServer(body: McpServerInput): Promise<McpServer> {
  return parseJson(
    await ceApi("/api/mcp/servers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to add server",
  );
}

export async function updateMcpServer(
  name: string,
  body: McpServerInput,
): Promise<McpServer> {
  return parseJson(
    await ceApi(`/api/mcp/servers/${encodeURIComponent(name)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Failed to update server",
  );
}

export async function deleteMcpServer(name: string): Promise<void> {
  await parseJson(
    await ceApi(`/api/mcp/servers/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),
    "Failed to delete server",
  );
}

export async function setMcpServerEnabled(
  name: string,
  enabled: boolean,
): Promise<void> {
  await parseJson(
    await ceApi(`/api/mcp/servers/${encodeURIComponent(name)}/enabled`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    }),
    "Failed to update server",
  );
}

export async function testMcpServer(
  name: string,
): Promise<{ ok: boolean; tools: string[]; error?: string }> {
  return parseJson(
    await ceApi(`/api/mcp/servers/${encodeURIComponent(name)}/test`, {
      method: "POST",
    }),
    "Connection test failed",
  );
}
```

### 4. `frontend/src/app/(workspace)/admin/mcp/page.tsx` - full rewrite

Rewrite the page completely. Keep the same route and PageHeader pattern. Study
`settings/web-search/page.tsx` and `settings/governance/page.tsx` for dialog and list
patterns to match exactly.

Key UI elements:

**Server list** (one `Card variant="outlined"` per server):
- Server name in `Typography variant="subtitle1"` with `fontWeight={600}`.
- Transport badge: `<Chip size="small" label="stdio" />` or `"http"` or `"sse"`.
- Status badge: `<Chip size="small" color="success" label="Enabled" />` or
  `<Chip size="small" label="Disabled" />`.
- If `server.auto_spawned`: `<Chip size="small" label="Auto-added" variant="outlined" />`.
- Tool chips: render `server.tools` as small outlined chips (max 8, then "+N more").
- `Switch` for enable/disable: calls `setMcpServerEnabled` on change.
- "List tools" button: calls `testMcpServer`, updates tools display for that server.
- "Edit" button: opens the edit dialog pre-filled.
- "Delete" `IconButton` with `DeleteIcon`: calls `deleteMcpServer` after `window.confirm`.

**Add/Edit dialog** (single dialog, reused):

```
Transport: [stdio] [HTTP/SSE]   <- ToggleButtonGroup

If stdio:
  Command *      [npx                              ]
  Arguments      [-y, @modelcontextprotocol/server-filesystem, /tmp]
                 (comma-separated or one per line)

If HTTP/SSE:
  URL *          [https://my-mcp-server.example.com/mcp]
  Transport type [Auto] [SSE]   <- radio or toggle

Name *           [filesystem                       ]

Environment variables   [+ Add variable]
  KEY     VALUE (password field)
  [KEY1]  [••••••]  [x]
  [KEY2]  [••••••]  [x]
```

State shape for the dialog:

```typescript
type DialogState = {
  open: boolean;
  editing: McpServer | null; // null = adding new
  transport: "stdio" | "http";
  name: string;
  command: string;
  args: string; // comma-separated string, split on save
  url: string;
  sseOverride: boolean;
  envPairs: Array<{ key: string; value: string }>;
};
```

On save:
- Split `args` on commas: `args.split(",").map(s => s.trim()).filter(Boolean)`.
- Build `env` object from `envPairs` (skip pairs with empty key).
- Call `addMcpServer(body)` or `updateMcpServer(editing.name, body)`.
- After success: reload server list, close dialog.

Validation before calling API:
- Name must not be empty.
- stdio transport: command must not be empty.
- http transport: url must start with `http://` or `https://`.

Do NOT show the "Auto-added" chip in the edit dialog; auto-spawned flag is preserved
server-side.

**Page-level actions** (in `PageHeader actions` prop):

```tsx
actions={
  <Button variant="contained" startIcon={<AddIcon />} onClick={() => openAddDialog()}>
    Add server
  </Button>
}
```

**Empty state**: use the existing `EmptyState` component (already imported).

**Error handling**: `Alert severity="error"` at top, cleared on next successful action.

---

## Acceptance criteria

1. `GET /api/mcp/servers` returns `transport`, `command`, `args`, `env` (redacted),
   `enabled`, `auto_spawned` for each server.
2. `PUT /api/mcp/servers/{name}/enabled` with `{ enabled: false }` writes
   `enabled: false` to `config.yaml` and returns `{ ok: true }`.
3. Adding a stdio server via the UI form (e.g. name=`filesystem`,
   command=`npx`, args=`-y, @modelcontextprotocol/server-filesystem, /tmp`) saves it to
   `config.yaml` correctly.
4. Adding an HTTP server via the URL field works exactly as before.
5. Editing an existing server changes its config without changing the `auto_spawned`
   flag.
6. "List tools" button populates tool chips in that server's row.
7. Environment variable fields are password-type inputs; existing values are shown as
   `"***"` placeholder only (the server's `env` map from the API already redacts them).
8. The enable/disable switch is reflected immediately in the UI after the API call.
9. Deleting a server with `window.confirm` removes it from the list.
10. No TypeScript compile errors on the changed files.

---

## What this prompt does NOT do

- Does not add a catalog tab (that is prompt 160).
- Does not add autonomous spawning (that is prompt 161).
- Does not add `register_server_runtime()` to `mcp_tool.py`; restarting Keprix is still
  required to pick up newly added servers after this prompt.
