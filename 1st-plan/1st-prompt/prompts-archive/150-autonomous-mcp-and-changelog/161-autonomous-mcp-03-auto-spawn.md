# Keprix Prompt 161: Autonomous MCP - Auto Spawn

## Purpose

Give the Keprix agent the ability to spawn any MCP it needs during a task without the
user adding it manually. The agent gets a `keprix_spawn_mcp` tool it can call
explicitly when it recognises a missing capability. Once spawned, the server is:

1. Connected live in the current session (no restart needed).
2. Persisted in `config.yaml` as `auto_spawned: true` so it reloads next session.
3. Visible in `/admin/mcp` with an "Auto-added" badge.

When the required server needs credentials that are not in the Vault or env, the agent
is told exactly what credential to ask the user for, with a direct link to the settings
page. It does not silently fail.

This is off by default (`KEPRIX_AUTO_MCP_SPAWN=false`). The operator turns it on to
enable the capability.

---

## Dependencies

- Prompts 159 and 160 must be complete.
- `src/keprix/tools/mcp_tool.py` - must add `register_server_runtime()` and
  `unregister_server_runtime()` (see below).
- `src/keprix/keprix_cli/mcp_catalog.py` - `get_entry()`, `find_by_tags()`.
- `src/keprix/keprix_cli/mcp_config.py` - `_save_mcp_server()`, `_get_mcp_servers()`.
- `src/keprix/toolsets.py` or wherever built-in tool registration happens - to
  conditionally register `keprix_spawn_mcp`.
- `src/keprix/keprix_cli/web_server.py` - add two new API endpoints.
- Vault access: `src/keprix/tools/credential_files.py` or the vault helper used by
  other tools (read the existing pattern before writing new code).

---

## What to build

### 1. `mcp_tool.py`: add `register_server_runtime()` and `unregister_server_runtime()`

Read `mcp_tool.py` fully before adding these. Follow the exact patterns used by
existing connect/disconnect logic. Add at the end of the module.

```python
def register_server_runtime(name: str, config: dict) -> None:
    """
    Connect a new MCP server in the live session.

    Writes the server into the internal ``_servers`` registry and starts its
    connection task on ``_mcp_loop``.  The server is then immediately available
    for tool calls without restarting Keprix.

    ``config`` has the same shape as a ``mcp_servers`` entry in config.yaml::

        {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            "env": {},          # optional
            "timeout": 120,     # optional
        }

    Raises ``RuntimeError`` if the MCP event loop is not running (keprix was
    started without MCP support).
    Raises ``ValueError`` if ``name`` is already registered.
    """
    global _servers, _mcp_loop, _lock

    with _lock:
        if _mcp_loop is None or not _mcp_loop.is_running():
            raise RuntimeError(
                "MCP event loop is not running. "
                "Start keprix with MCP support enabled."
            )
        if name in _servers:
            raise ValueError(f"MCP server '{name}' is already registered")

    # Use the internal helper that _load_mcp_servers_from_config calls per entry.
    # Read how existing servers are started and replicate exactly.
    # The exact function name depends on what is in mcp_tool.py at build time;
    # search for where ``asyncio.run_coroutine_threadsafe`` is called to start a
    # server and follow the same pattern.
    _start_server_on_loop(name, config)
    logger.info("MCP server '%s' registered at runtime", name)


def unregister_server_runtime(name: str) -> None:
    """
    Disconnect and remove a server from the live session.

    Does not modify config.yaml. If the name is not registered, this is a no-op.
    """
    global _servers, _lock

    with _lock:
        if name not in _servers:
            return

    _stop_server(name)
    logger.info("MCP server '%s' unregistered at runtime", name)
```

`_start_server_on_loop` and `_stop_server` are the names used by the existing code.
If the actual names differ, use whatever is there. The key invariant is: after
`register_server_runtime()` returns, the server's tools are available to the agent on
the next tool call.

### 2. `src/keprix/tools/auto_mcp_spawn.py` (NEW FILE)

```python
"""
Autonomous MCP Spawn Manager.

The ``keprix_spawn_mcp`` tool is the agent-facing interface. When the agent
determines it needs a capability that no loaded MCP currently provides, it calls
this tool with the capability description or a specific catalog key.

Flow:
    1. Agent calls keprix_spawn_mcp(capability="web search") or
       keprix_spawn_mcp(catalog_name="brave-search").
    2. If catalog_name given, look it up directly.
       Otherwise, call find_by_tags() with keywords extracted from capability.
    3. Check whether required env vars exist in Vault or os.environ.
    4. If credentials missing: return a user-facing message with the credential
       name and a link to /admin/mcp. Do NOT spawn.
    5. If all credentials present (or none needed):
       a. Call _save_mcp_server() with auto_spawned=True.
       b. Call register_server_runtime() to activate in the live session.
       c. Return success message listing the new tool names.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("keprix.auto_mcp_spawn")


# ---------------------------------------------------------------------------
# Credential check helpers
# ---------------------------------------------------------------------------

def _check_credentials(required_env: List[str]) -> Dict[str, str]:
    """
    Return a dict of { env_var_name: value } for all required vars that are
    available.  Checks os.environ first, then the Keprix Vault.

    Returns an incomplete dict if some vars are missing; caller checks len.
    """
    found: Dict[str, str] = {}
    for var in required_env:
        value = os.environ.get(var)
        if not value:
            # Try Vault
            try:
                from tools.credential_files import read_secret  # or vault helper
                value = read_secret(var)
            except Exception:
                pass
        if value:
            found[var] = value
    return found


def _missing_credentials(entry: Dict[str, Any]) -> List[str]:
    """Return a list of env var names that are required but not available."""
    required = entry.get("required_env", [])
    found = _check_credentials(required)
    return [v for v in required if v not in found]


# ---------------------------------------------------------------------------
# Core spawn logic
# ---------------------------------------------------------------------------

def spawn_mcp(
    *,
    catalog_name: Optional[str] = None,
    capability: Optional[str] = None,
    name_override: Optional[str] = None,
    env_override: Optional[Dict[str, str]] = None,
) -> str:
    """
    Resolve, connect, and persist an MCP server.

    Returns a string message suitable for returning to the agent.
    Never raises; returns an error string instead.
    """
    from keprix_cli.mcp_catalog import get_entry, find_by_tags
    from keprix_cli.mcp_config import _get_mcp_servers, _save_mcp_server

    # -- Resolve catalog entry ------------------------------------------------
    entry: Optional[Dict[str, Any]] = None

    if catalog_name:
        try:
            entry = get_entry(catalog_name)
        except KeyError:
            return (
                f"Unknown catalog entry: '{catalog_name}'. "
                f"Call list_mcp_catalog() to see available entries."
            )
    elif capability:
        # Extract keywords from capability string and search by tags
        keywords = [w.strip().lower() for w in capability.replace(",", " ").split() if len(w) > 2]
        matches = find_by_tags(keywords)
        if not matches:
            return (
                f"No catalog entry found matching '{capability}'. "
                f"You can add a custom MCP server at /admin/mcp."
            )
        entry = matches[0]  # Use best match (first hit)
    else:
        return "Provide either catalog_name or capability."

    server_name = (name_override or entry["key"]).strip()

    # -- Check for duplicates -------------------------------------------------
    existing = _get_mcp_servers()
    if server_name in existing:
        return (
            f"MCP server '{server_name}' is already configured. "
            f"Its tools are available with the prefix 'mcp_{server_name}_'."
        )

    # -- Credential check -----------------------------------------------------
    missing = _missing_credentials(entry)
    if missing and not env_override:
        cred_list = ", ".join(missing)
        return (
            f"To add '{entry['label']}', I need: {cred_list}. "
            f"Please add the credential(s) at /admin/mcp and then try again, "
            f"or provide them via env_override."
        )

    # Build final env from Vault/env + any provided override
    env: Dict[str, str] = {}
    if entry.get("required_env"):
        env = _check_credentials(entry["required_env"])
    if env_override:
        env.update(env_override)

    # -- Build config dict ----------------------------------------------------
    server_config: Dict[str, Any] = {}
    if entry.get("command"):
        server_config["command"] = entry["command"]
        if entry.get("args"):
            server_config["args"] = list(entry["args"])
    if entry.get("url"):
        server_config["url"] = entry["url"]
    if env:
        server_config["env"] = env
    server_config["auto_spawned"] = True

    # -- Persist to config.yaml -----------------------------------------------
    if not _save_mcp_server(server_name, server_config):
        return (
            f"Could not save server '{server_name}': security validation failed. "
            f"This catalog entry may not be safe to use."
        )

    # -- Activate in live session ---------------------------------------------
    try:
        from tools.mcp_tool import register_server_runtime
        register_server_runtime(server_name, server_config)
        live_msg = "and is active in this session"
    except RuntimeError:
        # MCP loop not running (e.g. Keprix started without MCP)
        live_msg = "but will activate after the next Keprix restart"
    except ValueError:
        # Already registered (race condition)
        live_msg = "and is already active"
    except Exception as exc:
        logger.warning("register_server_runtime failed for %s: %s", server_name, exc)
        live_msg = "but could not be activated live (restart Keprix to use it)"

    label = entry.get("label", server_name)
    tags = ", ".join(entry.get("capability_tags", [])[:4])
    return (
        f"Added '{label}' MCP server as '{server_name}' {live_msg}. "
        f"Capabilities: {tags}. "
        f"Tools are available with the prefix 'mcp_{server_name}_'. "
        f"You can manage it at /admin/mcp."
    )


# ---------------------------------------------------------------------------
# Tool wrapper (called by the tool registry)
# ---------------------------------------------------------------------------

def keprix_spawn_mcp_tool(params: dict) -> str:
    """
    Tool handler for the keprix_spawn_mcp built-in tool.

    Expected params:
        catalog_name   str  (optional) - exact catalog key, e.g. "brave-search"
        capability     str  (optional) - free-text, e.g. "search the web"
        name           str  (optional) - override the server name
        env            dict (optional) - credential key-value pairs
    """
    return spawn_mcp(
        catalog_name=params.get("catalog_name"),
        capability=params.get("capability"),
        name_override=params.get("name"),
        env_override=params.get("env") or None,
    )
```

### 3. Register `keprix_spawn_mcp` as a built-in tool

Find where built-in tools are registered (likely `toolsets.py` or the tool registry
in the agent startup path). Follow the existing registration pattern exactly.

Register the tool ONLY when `KEPRIX_AUTO_MCP_SPAWN=true`:

```python
import os

if os.environ.get("KEPRIX_AUTO_MCP_SPAWN", "false").lower() == "true":
    from tools.auto_mcp_spawn import keprix_spawn_mcp_tool

    TOOL_REGISTRY.register(
        name="keprix_spawn_mcp",
        description=(
            "Add and activate an MCP server from the built-in catalog. "
            "Call this when you need a capability that no existing tool provides. "
            "Provide either catalog_name (exact key) or capability (free-text description). "
            "The server is saved for future sessions and its tools are immediately available."
        ),
        parameters={
            "type": "object",
            "properties": {
                "catalog_name": {
                    "type": "string",
                    "description": (
                        "Exact catalog key, e.g. 'brave-search', 'github', 'filesystem'. "
                        "Use GET /api/mcp/catalog to list all keys."
                    ),
                },
                "capability": {
                    "type": "string",
                    "description": (
                        "Free-text description of the needed capability, "
                        "e.g. 'search the web', 'read local files', 'query GitHub'. "
                        "Used when catalog_name is not known."
                    ),
                },
                "name": {
                    "type": "string",
                    "description": "Optional override for the server name in config.",
                },
                "env": {
                    "type": "object",
                    "description": "Optional credential key-value pairs for the server.",
                    "additionalProperties": {"type": "string"},
                },
            },
        },
        handler=keprix_spawn_mcp_tool,
    )
```

The `TOOL_REGISTRY.register()` call must exactly match how existing built-in tools are
registered. Read the registration for another tool (e.g. `web_search` or `memory_tool`)
in `toolsets.py` and replicate the pattern.

### 4. `web_server.py`: auto-spawn status endpoints

Add these two endpoints so the frontend can query auto-spawn state:

```python
@app.get("/api/mcp/auto-spawn/status")
async def get_auto_spawn_status():
    """Return whether auto-spawn is enabled and the list of auto-spawned servers."""
    from keprix_cli.mcp_config import _get_mcp_servers
    enabled = os.environ.get("KEPRIX_AUTO_MCP_SPAWN", "false").lower() == "true"
    servers = _get_mcp_servers()
    auto_spawned = [
        name for name, cfg in servers.items()
        if cfg.get("auto_spawned") is True
    ]
    return {"enabled": enabled, "auto_spawned_servers": auto_spawned}


@app.delete("/api/mcp/auto-spawn/{name}")
async def remove_auto_spawned_server(name: str, profile: Optional[str] = None):
    """Remove an auto-spawned server (used by the UI's 'Remove auto-added' action)."""
    from keprix_cli.mcp_config import _get_mcp_servers, _remove_mcp_server

    with _profile_scope(profile):
        servers = _get_mcp_servers()
    if name not in servers:
        raise HTTPException(status_code=404, detail=f"Server '{name}' not found")
    if not servers[name].get("auto_spawned"):
        raise HTTPException(
            status_code=400,
            detail=f"Server '{name}' was not auto-spawned; use the regular delete endpoint",
        )

    # Also unregister from live session if possible
    try:
        from tools.mcp_tool import unregister_server_runtime
        unregister_server_runtime(name)
    except Exception:
        pass

    with _profile_scope(profile):
        _remove_mcp_server(name)

    return {"ok": True}
```

### 5. `frontend/src/lib/admin-api.ts`: auto-spawn API functions

```typescript
export type AutoSpawnStatus = {
  enabled: boolean;
  auto_spawned_servers: string[];
};

export async function fetchAutoSpawnStatus(): Promise<AutoSpawnStatus> {
  return parseJson<AutoSpawnStatus>(
    await ceApi("/api/mcp/auto-spawn/status"),
    "Failed to load auto-spawn status",
  );
}

export async function removeAutoSpawnedServer(name: string): Promise<void> {
  await parseJson(
    await ceApi(`/api/mcp/auto-spawn/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),
    "Failed to remove auto-spawned server",
  );
}
```

### 6. `frontend/src/app/(workspace)/admin/mcp/page.tsx`: auto-spawn status panel

Add a status panel at the top of the "My servers" tab, shown only when `SWR` fetches
from `/api/mcp/auto-spawn/status`.

```
[Auto-spawn: Enabled]   3 servers added automatically

When auto-spawn is off, the agent cannot add MCPs. Turn it on by setting
KEPRIX_AUTO_MCP_SPAWN=true in your .env.
```

If `status.enabled` is false:
```
[Auto-spawn: Off]   Enable via KEPRIX_AUTO_MCP_SPAWN=true in your environment.
```

"3 servers added automatically" is a count derived from
`status.auto_spawned_servers.length`. No list needed here; the server list below already
shows the "Auto-added" badge per server.

This panel is an `Alert severity="info"` with `sx={{ mb: 2 }}` and the text above.
No additional components needed.

---

## Acceptance criteria

1. `register_server_runtime("filesystem", config)` connects a filesystem MCP in the
   live session without restarting Keprix. Tools `mcp_filesystem_read_file` etc.
   appear immediately.

2. `unregister_server_runtime("filesystem")` removes the tools from the live session.

3. `keprix_spawn_mcp_tool({"catalog_name": "filesystem"})` with `KEPRIX_AUTO_MCP_SPAWN=true`:
   - Writes entry to `config.yaml` with `auto_spawned: true`.
   - Calls `register_server_runtime`.
   - Returns a string containing "active in this session".

4. `keprix_spawn_mcp_tool({"catalog_name": "brave-search"})` with no `BRAVE_API_KEY` in
   env or Vault:
   - Does NOT write to `config.yaml`.
   - Returns a string containing "BRAVE_API_KEY" and "/admin/mcp".

5. `keprix_spawn_mcp_tool({"capability": "search the web"})` matches `brave-search` or
   `fetch` from the catalog.

6. `keprix_spawn_mcp` tool is NOT in the tool list when
   `KEPRIX_AUTO_MCP_SPAWN=false` (default).

7. `keprix_spawn_mcp` tool IS in the tool list when
   `KEPRIX_AUTO_MCP_SPAWN=true`.

8. `GET /api/mcp/auto-spawn/status` returns `{ "enabled": true/false, "auto_spawned_servers": [...] }`.

9. `DELETE /api/mcp/auto-spawn/filesystem` removes it from `config.yaml` and calls
   `unregister_server_runtime`.

10. The auto-spawn status panel renders in the `/admin/mcp` page with the correct
    enabled/disabled state.

---

## What this prompt does NOT do

- Does not intercept tool-not-found errors to spawn MCPs silently. The agent must
  explicitly call `keprix_spawn_mcp`. Silent interception is a future option.
- Does not modify the existing `mcp_tool.py` auth, reconnect, or sampling logic.
- Does not add a UI for toggling `KEPRIX_AUTO_MCP_SPAWN`; it is an env var set by the
  operator.

---

## Tests to write

### `tests/test_auto_mcp_spawn.py`

```python
def test_spawn_no_credentials_returns_message():
    # brave-search requires BRAVE_API_KEY; env is clean
    result = spawn_mcp(catalog_name="brave-search")
    assert "BRAVE_API_KEY" in result
    assert "/admin/mcp" in result

def test_spawn_filesystem_no_credentials_needed(mock_save_server, mock_register_runtime):
    result = spawn_mcp(catalog_name="filesystem")
    assert "active in this session" in result
    mock_save_server.assert_called_once()
    mock_register_runtime.assert_called_once()

def test_spawn_duplicate_returns_message(mock_get_servers_with_filesystem):
    result = spawn_mcp(catalog_name="filesystem")
    assert "already configured" in result

def test_spawn_by_capability_matches_tags():
    from keprix_cli.mcp_catalog import find_by_tags
    matches = find_by_tags(["web", "search"])
    assert any(e["key"] == "brave-search" for e in matches)

def test_spawn_unknown_catalog_name():
    result = spawn_mcp(catalog_name="does-not-exist")
    assert "Unknown catalog entry" in result

def test_tool_not_registered_when_flag_off(monkeypatch):
    monkeypatch.setenv("KEPRIX_AUTO_MCP_SPAWN", "false")
    # Re-import toolsets and check tool registry does not contain keprix_spawn_mcp
    ...

def test_tool_registered_when_flag_on(monkeypatch):
    monkeypatch.setenv("KEPRIX_AUTO_MCP_SPAWN", "true")
    # Re-import toolsets and check tool registry contains keprix_spawn_mcp
    ...
```
