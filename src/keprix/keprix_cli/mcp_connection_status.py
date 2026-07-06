"""Connection status helpers for MCP admin API responses."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

_last_test_results: Dict[str, Tuple[bool, str]] = {}


def record_mcp_test_result(name: str, ok: bool, error: str = "") -> None:
    """Store the outcome of POST /api/mcp/servers/{name}/test."""
    _last_test_results[name] = (bool(ok), str(error or ""))


def clear_mcp_test_result(name: str) -> None:
    _last_test_results.pop(name, None)


def _catalog_required_env(server_name: str) -> List[str]:
    try:
        from keprix_cli.autonomous_mcp_catalog import get_entry

        return list(get_entry(server_name).get("required_env") or [])
    except KeyError:
        return []


def _env_var_satisfied(var_name: str, cfg: Dict[str, Any]) -> bool:
    from keprix_cli.config import get_env_value

    env_block = cfg.get("env") or {}
    if str(env_block.get(var_name, "")).strip():
        return True
    if get_env_value(var_name):
        return True
    return bool(str(os.environ.get(var_name, "")).strip())


def missing_required_env(server_name: str, cfg: Dict[str, Any]) -> List[str]:
    """Return required env var names that are not configured."""
    required = _catalog_required_env(server_name)
    return [var for var in required if not _env_var_satisfied(var, cfg)]


def _runtime_connect_error(server_name: str) -> Optional[str]:
    try:
        from tools.mcp_tool import get_mcp_status

        for entry in get_mcp_status():
            if entry.get("name") == server_name:
                if entry.get("status") == "failed":
                    return str(entry.get("error") or "Connection failed")
    except Exception:
        pass
    return None


def connection_fields(name: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Compute oauth_connected, connection_status, and connection_error."""
    from keprix_cli.mcp_config import _oauth_tokens_present

    enabled = cfg.get("enabled", True) is not False
    auth = cfg.get("auth")
    oauth_connected = bool(auth == "oauth" and _oauth_tokens_present(name))

    connection_error = _runtime_connect_error(name)
    if name in _last_test_results:
        ok, err = _last_test_results[name]
        if not ok and err:
            connection_error = err

    if not enabled:
        status = "disabled"
    elif auth == "oauth":
        if not oauth_connected:
            status = "needs_oauth"
        elif connection_error:
            status = "error"
        else:
            status = "connected"
    else:
        missing = missing_required_env(name, cfg)
        if missing:
            status = "needs_credentials"
        elif connection_error:
            status = "error"
        elif name in _last_test_results:
            status = "connected" if _last_test_results[name][0] else "error"
        else:
            status = "connected"

    return {
        "oauth_connected": oauth_connected,
        "connection_status": status,
        "connection_error": connection_error,
    }
