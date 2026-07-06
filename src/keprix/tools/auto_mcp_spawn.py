"""
Autonomous MCP Spawn Manager.

The ``keprix_spawn_mcp`` tool is the agent-facing interface. When the agent
determines it needs a capability that no loaded MCP currently provides, it calls
this tool with the capability description or a specific catalog key.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("keprix.auto_mcp_spawn")


def _check_credentials(required_env: List[str]) -> Dict[str, str]:
    """Return env var values found in os.environ or ~/.keprix/.env."""
    found: Dict[str, str] = {}
    for var in required_env:
        value = os.environ.get(var)
        if not value:
            try:
                from keprix_cli.config import get_env_value

                value = get_env_value(var)
            except Exception:
                pass
        if value:
            found[var] = str(value)
    return found


def _missing_credentials(entry: Dict[str, Any]) -> List[str]:
    """Return required env var names that are not available."""
    required = entry.get("required_env", [])
    found = _check_credentials(required)
    return [v for v in required if v not in found]


def spawn_mcp(
    *,
    catalog_name: Optional[str] = None,
    capability: Optional[str] = None,
    name_override: Optional[str] = None,
    env_override: Optional[Dict[str, str]] = None,
) -> str:
    """Resolve, connect, and persist an MCP server. Returns an agent-facing message."""
    from keprix_cli.autonomous_mcp_catalog import find_by_tags, get_entry
    from keprix_cli.mcp_config import _get_mcp_servers, _save_mcp_server

    entry: Optional[Dict[str, Any]] = None

    if catalog_name:
        try:
            entry = get_entry(catalog_name)
        except KeyError:
            return (
                f"Unknown catalog entry: '{catalog_name}'. "
                f"Call GET /api/mcp/catalog to see available entries."
            )
    elif capability:
        keywords = [
            w.strip().lower()
            for w in capability.replace(",", " ").split()
            if len(w.strip()) > 2
        ]
        matches = find_by_tags(keywords)
        if not matches:
            return (
                f"No catalog entry found matching '{capability}'. "
                f"You can add a custom MCP server at /admin/mcp."
            )
        entry = matches[0]
    else:
        return "Provide either catalog_name or capability."

    server_name = (name_override or entry["key"]).strip()
    existing = _get_mcp_servers()
    if server_name in existing:
        return (
            f"MCP server '{server_name}' is already configured. "
            f"Its tools are available with the prefix 'mcp_{server_name}_'."
        )

    env: Dict[str, str] = {}
    if entry.get("required_env"):
        env = _check_credentials(entry["required_env"])
    if env_override:
        env.update({k: v for k, v in env_override.items() if v})

    missing = [v for v in entry.get("required_env", []) if v not in env]
    if missing:
        cred_list = ", ".join(missing)
        return (
            f"To add '{entry['label']}', I need: {cred_list}. "
            f"Please add the credential(s) at /admin/mcp and then try again, "
            f"or provide them via env."
        )

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

    if not _save_mcp_server(server_name, server_config):
        return (
            f"Could not save server '{server_name}': security validation failed. "
            f"This catalog entry may not be safe to use."
        )

    try:
        from tools.mcp_tool import register_server_runtime

        register_server_runtime(server_name, server_config)
        live_msg = "and is active in this session"
    except RuntimeError:
        live_msg = "but will activate after the next Keprix restart"
    except ValueError:
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


def keprix_spawn_mcp_tool(params: dict) -> str:
    """Tool handler for the keprix_spawn_mcp built-in tool."""
    return spawn_mcp(
        catalog_name=params.get("catalog_name"),
        capability=params.get("capability"),
        name_override=params.get("name"),
        env_override=params.get("env") or None,
    )


def check_auto_mcp_spawn_enabled() -> bool:
    """Gate tool registration on auto-spawn settings (env or config.yaml)."""
    from keprix_cli.mcp_spawn_settings import is_auto_mcp_spawn_enabled

    return is_auto_mcp_spawn_enabled()


KEPRIX_SPAWN_MCP_SCHEMA = {
    "name": "keprix_spawn_mcp",
    "description": (
        "Add and activate an MCP server from the built-in catalog. "
        "Call this when you need a capability that no existing tool provides. "
        "Provide either catalog_name (exact key) or capability (free-text description). "
        "The server is saved for future sessions and its tools are immediately available."
    ),
    "parameters": {
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
}


from tools.registry import registry

registry.register(
    name="keprix_spawn_mcp",
    toolset="auto_mcp_spawn",
    schema=KEPRIX_SPAWN_MCP_SCHEMA,
    handler=lambda args, **kw: keprix_spawn_mcp_tool(args),
    check_fn=check_auto_mcp_spawn_enabled,
)
