# Keprix Prompt 160: Autonomous MCP - Catalog

## Purpose

Give Keprix a curated list of well-known MCP servers that both the UI and the
autonomous spawn mechanism (prompt 161) can use. After this prompt, the `/admin/mcp`
page has a "Browse catalog" tab where users can add MCPs with one click, and a new
`GET /api/mcp/catalog` endpoint serves the catalog to any caller.

---

## Dependencies

- Prompt 159 complete (the upgraded MCP management page is already in place).
- `src/keprix/keprix_cli/mcp_config.py` - `_save_mcp_server` (used by the add-from-catalog route).
- `src/keprix/keprix_cli/web_server.py` - existing MCP routes (add the catalog route here).
- `frontend/src/lib/admin-api.ts` - add `fetchMcpCatalog` and `addMcpFromCatalog`.
- `frontend/src/app/(workspace)/admin/mcp/page.tsx` - add a catalog tab.

---

## What to build

### 1. `src/keprix/keprix_cli/mcp_catalog.py` (NEW FILE)

```python
"""
Curated catalog of well-known MCP servers that Keprix can suggest or
auto-spawn. Each entry is a dict with fields understood by MCPServerCreate
and the auto-spawn manager.

Fields:
    key          Stable identifier used as the default server name.
    label        Human-readable display name.
    description  One sentence describing what the server does.
    transport    "stdio" or "http".
    command      Executable for stdio servers (usually "npx").
    args         Argument list for stdio servers.
    url          Base URL for HTTP/SSE servers (template, may be None).
    required_env List of env var names the server needs; empty = no credentials.
    capability_tags  List of lowercase strings describing capabilities. Used by
                     the auto-spawn matcher in prompt 161.
    homepage     Documentation URL shown in the UI (optional).
    auto_spawnable   True if the server can be spawned without user credentials.
                     Set to True only for servers where required_env is empty.
"""

from typing import Any, Dict, List

MCP_CATALOG: List[Dict[str, Any]] = [
    {
        "key": "filesystem",
        "label": "Filesystem",
        "description": "Read and write local files and directories.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem"],
        "required_env": [],
        "capability_tags": ["files", "read", "write", "local"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
        "auto_spawnable": True,
    },
    {
        "key": "fetch",
        "label": "Fetch",
        "description": "Fetch web pages and convert them to markdown.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-fetch"],
        "required_env": [],
        "capability_tags": ["web", "http", "fetch", "scrape"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/fetch",
        "auto_spawnable": True,
    },
    {
        "key": "memory",
        "label": "Memory",
        "description": "Persistent entity-based knowledge graph memory.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "required_env": [],
        "capability_tags": ["memory", "entities", "knowledge", "graph"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/memory",
        "auto_spawnable": True,
    },
    {
        "key": "sequential-thinking",
        "label": "Sequential Thinking",
        "description": "Dynamic problem-solving through structured thought sequences.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        "required_env": [],
        "capability_tags": ["reasoning", "planning", "thinking", "analysis"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking",
        "auto_spawnable": True,
    },
    {
        "key": "git",
        "label": "Git",
        "description": "Read git history, diffs, and blame across local repositories.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-git"],
        "required_env": [],
        "capability_tags": ["git", "version-control", "code", "history"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/git",
        "auto_spawnable": True,
    },
    {
        "key": "time",
        "label": "Time",
        "description": "Current time and timezone conversion.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-time"],
        "required_env": [],
        "capability_tags": ["time", "date", "timezone", "clock"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/time",
        "auto_spawnable": True,
    },
    {
        "key": "sqlite",
        "label": "SQLite",
        "description": "Query and modify a local SQLite database.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sqlite"],
        "required_env": [],
        "capability_tags": ["database", "sql", "sqlite", "local"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite",
        "auto_spawnable": True,
    },
    {
        "key": "puppeteer",
        "label": "Puppeteer",
        "description": "Control a headless browser for web automation and screenshots.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "required_env": [],
        "capability_tags": ["browser", "automation", "screenshot", "puppeteer"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/puppeteer",
        "auto_spawnable": True,
    },
    {
        "key": "github",
        "label": "GitHub",
        "description": "Search repos, read files, manage issues and PRs via GitHub API.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "required_env": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
        "capability_tags": ["github", "code", "repos", "issues", "prs"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/github",
        "auto_spawnable": False,
    },
    {
        "key": "brave-search",
        "label": "Brave Search",
        "description": "Web and local search powered by the Brave Search API.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-brave-search"],
        "required_env": ["BRAVE_API_KEY"],
        "capability_tags": ["web", "search", "brave"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/brave-search",
        "auto_spawnable": False,
    },
    {
        "key": "postgres",
        "label": "PostgreSQL",
        "description": "Read-only query access to a PostgreSQL database.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres"],
        "required_env": ["POSTGRES_URL"],
        "capability_tags": ["database", "sql", "postgres"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/postgres",
        "auto_spawnable": False,
    },
    {
        "key": "slack",
        "label": "Slack",
        "description": "Read channels and send messages via the Slack API.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-slack"],
        "required_env": ["SLACK_BOT_TOKEN", "SLACK_TEAM_ID"],
        "capability_tags": ["slack", "messaging", "team"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/slack",
        "auto_spawnable": False,
    },
    {
        "key": "google-maps",
        "label": "Google Maps",
        "description": "Geocoding, directions, and place search via Google Maps.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-google-maps"],
        "required_env": ["GOOGLE_MAPS_API_KEY"],
        "capability_tags": ["maps", "location", "geocoding", "directions"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/google-maps",
        "auto_spawnable": False,
    },
    {
        "key": "everything",
        "label": "Everything (Demo)",
        "description": "Test server exposing all MCP primitives. Use for development only.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-everything"],
        "required_env": [],
        "capability_tags": ["demo", "test", "development"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/everything",
        "auto_spawnable": True,
    },
]

# Lookup by key
_CATALOG_BY_KEY: Dict[str, Dict[str, Any]] = {e["key"]: e for e in MCP_CATALOG}


def get_catalog() -> List[Dict[str, Any]]:
    """Return the full catalog list."""
    return MCP_CATALOG


def get_entry(key: str) -> Dict[str, Any]:
    """Return a catalog entry by key, or raise KeyError."""
    entry = _CATALOG_BY_KEY.get(key)
    if not entry:
        raise KeyError(f"Unknown MCP catalog key: {key!r}")
    return entry


def find_by_tags(tags: List[str]) -> List[Dict[str, Any]]:
    """Return catalog entries that match ANY of the given capability tags."""
    tag_set = {t.lower() for t in tags}
    return [
        e for e in MCP_CATALOG
        if tag_set.intersection({ct.lower() for ct in e.get("capability_tags", [])})
    ]
```

### 2. `web_server.py`: add `GET /api/mcp/catalog` and `POST /api/mcp/catalog/{key}/add`

Add after the existing MCP routes:

```python
@app.get("/api/mcp/catalog")
async def list_mcp_catalog():
    """Return the curated MCP catalog."""
    from keprix_cli.mcp_catalog import get_catalog
    return {"catalog": get_catalog()}


@app.post("/api/mcp/catalog/{key}/add")
async def add_mcp_from_catalog(
    key: str,
    body: Optional[MCPCatalogAddBody] = None,
    profile: Optional[str] = None,
):
    """
    Add a catalog entry as a configured MCP server.

    Optional body fields:
        name: str     Override the server name (default: catalog key).
        env: dict     Provide required env vars (e.g. API keys).
    """
    from keprix_cli.mcp_catalog import get_entry
    from keprix_cli.mcp_config import _get_mcp_servers, _save_mcp_server

    try:
        entry = get_entry(key)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Catalog entry '{key}' not found")

    name = (body.name if body and body.name else key).strip()

    with _profile_scope(profile):
        existing = _get_mcp_servers()
    if name in existing:
        raise HTTPException(status_code=409, detail=f"Server '{name}' already exists")

    server_config: Dict[str, Any] = {}
    if entry.get("url"):
        server_config["url"] = entry["url"]
    if entry.get("command"):
        server_config["command"] = entry["command"]
        if entry.get("args"):
            server_config["args"] = list(entry["args"])
    if body and body.env:
        server_config["env"] = dict(body.env)
    # Tag as auto_spawned=False when added manually from the catalog
    server_config["auto_spawned"] = False

    with _profile_scope(profile):
        if not _save_mcp_server(name, server_config):
            raise HTTPException(
                status_code=400,
                detail=f"Server '{name}' rejected: suspicious configuration",
            )

    return _mcp_server_summary(name, server_config)
```

Add the body model near the other Pydantic models:

```python
class MCPCatalogAddBody(BaseModel):
    name: Optional[str] = None
    env: Dict[str, str] = {}
```

### 3. `frontend/src/lib/admin-api.ts`: add catalog types and functions

Add these types and functions. Do not remove any existing ones.

```typescript
export type McpCatalogEntry = {
  key: string;
  label: string;
  description: string;
  transport: "stdio" | "http";
  command?: string;
  args?: string[];
  required_env: string[];
  capability_tags: string[];
  homepage?: string;
  auto_spawnable: boolean;
};

export async function fetchMcpCatalog(): Promise<McpCatalogEntry[]> {
  const data = await parseJson<{ catalog: McpCatalogEntry[] }>(
    await ceApi("/api/mcp/catalog"),
    "Failed to load MCP catalog",
  );
  return data.catalog;
}

export async function addMcpFromCatalog(
  key: string,
  opts?: { name?: string; env?: Record<string, string> },
): Promise<McpServer> {
  return parseJson(
    await ceApi(`/api/mcp/catalog/${encodeURIComponent(key)}/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(opts ?? {}),
    }),
    "Failed to add from catalog",
  );
}
```

### 4. `frontend/src/app/(workspace)/admin/mcp/page.tsx`: add "Browse catalog" tab

Add a `Tabs` component to the page with two tabs: "My servers" and "Browse catalog".

The existing server list goes under "My servers" tab (unchanged).

The "Browse catalog" tab:

- Shows catalog entries as cards in a two-column grid on medium+ screens.
- Each card shows: label, description, transport badge, capability tag chips (first 4),
  "Requires: ENV_VAR1, ENV_VAR2" if `required_env` is not empty, and a homepage link.
- "Add" button in each card:
  - If `required_env` is empty: calls `addMcpFromCatalog(key)` directly and shows a
    success Alert.
  - If `required_env` is not empty: opens a credential dialog with one password input
    per required env var, then calls `addMcpFromCatalog(key, { env: {...} })`.
- If the server name already exists in "My servers", the button reads "Already added"
  and is disabled.
- After successfully adding from catalog, switch the active tab back to "My servers"
  and refresh the server list.

Credential dialog for catalog entries with required_env:

```
Add GitHub                                  [x]

This server requires credentials to connect.

  GITHUB_PERSONAL_ACCESS_TOKEN *   [          ]
  Get your token at github.com/settings/tokens

  [Cancel]           [Add server]
```

Tab state is local (`React.useState`). Use `useSWR` for both `/api/mcp/servers` and
`/api/mcp/catalog` fetches so both tabs load in parallel.

Import `Tabs`, `Tab` from `@mui/material`. Keep the existing imports.

---

## Acceptance criteria

1. `GET /api/mcp/catalog` returns 14 entries with all required fields.
2. `POST /api/mcp/catalog/filesystem/add` with no body adds `filesystem` to
   `config.yaml` with `command: npx` and `args: ["-y", "@modelcontextprotocol/server-filesystem"]`.
3. `POST /api/mcp/catalog/github/add` with `{ "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx" } }`
   saves the server with the env var.
4. `POST /api/mcp/catalog/filesystem/add` a second time returns 409.
5. The "Browse catalog" tab renders all 14 entries.
6. Clicking "Add" on `filesystem` (no credentials needed) adds it without showing a
   dialog and switches to "My servers".
7. Clicking "Add" on `github` opens a dialog with one password field for the PAT.
8. After adding from catalog, the entry appears in "My servers" with correct transport badge.
9. Entries already in "My servers" show "Already added" (disabled button) in the catalog.
10. No TypeScript compile errors on changed files.

---

## What this prompt does NOT do

- Does not wire the catalog into auto-spawn (that is prompt 161).
- Does not add `register_server_runtime()` to `mcp_tool.py`; a Keprix restart is still
  needed to activate newly added servers.
