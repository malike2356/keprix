"""MCP admin API routes (shared by dashboard web_server and main API).

Mount with ``app.include_router(router)``. On the workspace API (port 3333),
include with admin auth: ``dependencies=[Depends(require_admin)]``.
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from keprix_cli.config import load_config, redact_key, save_config, save_env_value

_log = logging.getLogger(__name__)
router = APIRouter(tags=["mcp-admin"])


@contextmanager
def _profile_scope(profile: Optional[str]):
    from keprix_cli.web_server import _profile_scope as _ws_profile_scope

    with _ws_profile_scope(profile):
        yield


# ---------------------------------------------------------------------------
# MCP server endpoints — list / add / remove / test.
#
# Wraps the same config data layer the CLI uses (keprix_cli.mcp_config), so
# servers managed here show up under `keprix mcp list` and vice versa.  Secrets
# in stdio `env` blocks are redacted on read; the agent picks them up from
# config.yaml at session start exactly as with CLI-added servers.
# ---------------------------------------------------------------------------


class MCPServerCreate(BaseModel):
    name: str
    url: Optional[str] = None
    command: Optional[str] = None
    args: List[str] = []
    # env: KEY=VALUE map for stdio servers (API keys, etc.)
    env: Dict[str, str] = {}
    # auth: "oauth" | "header" | None
    auth: Optional[str] = None
    # transport: "sse" for URL-based SSE servers (default: Streamable HTTP)
    transport: Optional[str] = None
    profile: Optional[str] = None


def _redact_mcp_env(env: Dict[str, Any]) -> Dict[str, str]:
    """Mask secret-shaped MCP env values for read responses."""
    out: Dict[str, str] = {}
    for k, v in (env or {}).items():
        try:
            out[str(k)] = redact_key(str(v)) if v else ""
        except Exception:
            out[str(k)] = "***"
    return out


def _mcp_server_summary(name: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    from keprix_cli.mcp_connection_status import connection_fields

    if cfg.get("command"):
        transport = "stdio"
    elif cfg.get("url"):
        transport = "sse" if cfg.get("transport") == "sse" else "http"
    else:
        transport = "unknown"
    summary = {
        "name": name,
        "transport": transport,
        "url": cfg.get("url"),
        "command": cfg.get("command"),
        "args": list(cfg.get("args") or []),
        "env": _redact_mcp_env(cfg.get("env") or {}),
        "auth": cfg.get("auth"),
        "enabled": cfg.get("enabled", True) is not False,
        "auto_spawned": bool(cfg.get("auto_spawned")),
        # Tool selection: list of enabled tool names, or None = all.
        "tools": cfg.get("tools"),
    }
    summary.update(connection_fields(name, cfg))
    return summary


@router.get("/api/mcp/servers")
async def list_mcp_servers(profile: Optional[str] = None):
    from keprix_cli.mcp_config import _get_mcp_servers

    with _profile_scope(profile):
        servers = _get_mcp_servers()
    return {
        "servers": [
            _mcp_server_summary(name, cfg) for name, cfg in sorted(servers.items())
        ]
    }


@router.post("/api/mcp/servers")
async def add_mcp_server(body: MCPServerCreate, profile: Optional[str] = None):
    from keprix_cli.mcp_config import _get_mcp_servers, _save_mcp_server

    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Server name is required")
    with _profile_scope(body.profile or profile):
        existing = _get_mcp_servers()
    if name in existing:
        raise HTTPException(status_code=409, detail=f"Server '{name}' already exists")
    if not body.url and not body.command:
        raise HTTPException(
            status_code=400,
            detail="Provide either a URL (HTTP/SSE server) or a command (stdio server)",
        )

    server_config: Dict[str, Any] = {}
    if body.url:
        server_config["url"] = body.url.strip()
        if body.transport == "sse":
            server_config["transport"] = "sse"
    if body.command:
        server_config["command"] = body.command.strip()
        if body.args:
            server_config["args"] = list(body.args)
    if body.env:
        server_config["env"] = dict(body.env)
    if body.auth:
        server_config["auth"] = body.auth

    try:
        with _profile_scope(body.profile or profile):
            if not _save_mcp_server(name, server_config):
                raise HTTPException(
                    status_code=400,
                    detail=f"Server '{name}' rejected: suspicious command/args configuration",
                )
    except HTTPException:
        raise
    except Exception as exc:
        _log.exception("POST /api/mcp/servers failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _mcp_server_summary(name, server_config)


@router.delete("/api/mcp/servers/{name}")
async def remove_mcp_server(name: str, profile: Optional[str] = None):
    from keprix_cli.mcp_config import _remove_mcp_server

    with _profile_scope(profile):
        removed = _remove_mcp_server(name)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Server '{name}' not found")
    return {"ok": True}


@router.post("/api/mcp/servers/{name}/test")
async def test_mcp_server(name: str, profile: Optional[str] = None):
    """Connect to the server, list its tools, disconnect.  Returns tool list."""
    from keprix_cli.mcp_config import _get_mcp_servers, _probe_single_server
    from keprix_cli.mcp_connection_status import record_mcp_test_result

    with _profile_scope(profile):
        servers = _get_mcp_servers()
    if name not in servers:
        raise HTTPException(status_code=404, detail=f"Server '{name}' not found")

    def _probe_scoped():
        # Re-enter the scope INSIDE the worker thread so call-time
        # resolution during the probe — env-placeholder expansion in
        # _resolve_mcp_server_config reading the profile's .env — sees the
        # selected profile, matching the config the server was saved into.
        # (asyncio.to_thread copies contextvars, but entering explicitly
        # keeps the lock-protected SKILLS_DIR swap balanced per-thread.)
        # The probe's dedicated MCP event-loop thread is covered too:
        # _run_on_mcp_loop wraps scheduled coroutines with the caller's
        # KEPRIX_HOME override (see mcp_tool._wrap_with_home_override), so
        # OAuth token stores resolve against the selected profile as well.
        with _profile_scope(profile):
            return _probe_single_server(name, servers[name])

    try:
        # Probe blocks on a dedicated MCP event loop — run in a thread so the
        # FastAPI event loop is never blocked.
        tools = await asyncio.to_thread(_probe_scoped)
    except Exception as exc:
        record_mcp_test_result(name, False, str(exc))
        return {
            "ok": False,
            "error": str(exc),
            "tools": [],
        }
    record_mcp_test_result(name, True)
    return {
        "ok": True,
        "tools": [{"name": t, "description": d} for t, d in tools],
    }


@router.post("/api/mcp/servers/{name}/oauth/start")
async def start_mcp_oauth(name: str, profile: Optional[str] = None):
    """Begin OAuth for an MCP server; return authorization URL for the UI."""
    from keprix_cli.mcp_config import _get_mcp_servers, begin_mcp_oauth_authorization

    with _profile_scope(profile):
        servers = _get_mcp_servers()
    if name not in servers:
        raise HTTPException(status_code=404, detail=f"Server '{name}' not found")
    server_config = servers[name]
    if server_config.get("auth") != "oauth":
        raise HTTPException(
            status_code=400,
            detail=f"Server '{name}' is not configured for OAuth",
        )

    def _start_scoped():
        with _profile_scope(profile):
            return begin_mcp_oauth_authorization(name, server_config)

    try:
        return await asyncio.to_thread(_start_scoped)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _log.exception("POST /api/mcp/servers/{name}/oauth/start failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


try:
    from keprix.auth.dependencies import get_current_user as _get_current_user

    async def _maybe_current_user(
        user: dict = Depends(_get_current_user),
    ) -> dict:
        return user

except Exception:  # pragma: no cover

    async def _maybe_current_user() -> Optional[dict]:
        return None


@router.get("/api/mcp/vault/secret-keys")
async def list_mcp_vault_secret_keys(
    user: Optional[dict] = Depends(_maybe_current_user),
):
    """List Vault item labels for MCP credential pickers (no secret values)."""
    from keprix_cli.mcp_vault_resolve import list_vault_secret_keys

    keys = await list_vault_secret_keys(user)
    return {"keys": keys}


class MCPEnabledToggle(BaseModel):
    enabled: bool
    profile: Optional[str] = None


@router.put("/api/mcp/servers/{name}/enabled")
async def set_mcp_server_enabled(
    name: str, body: MCPEnabledToggle, profile: Optional[str] = None
):
    """Enable or disable an MCP server (takes effect on next session/gateway).

    Toggles the ``enabled`` key on the server's config.yaml entry — the same
    flag the agent reads at startup.  Disabled servers stay in config so they
    can be re-enabled without re-entering their settings.
    """
    with _profile_scope(body.profile or profile):
        cfg = load_config()
        servers = cfg.get("mcp_servers")
        if not isinstance(servers, dict) or name not in servers:
            raise HTTPException(status_code=404, detail=f"Server '{name}' not found")
        if not isinstance(servers[name], dict):
            raise HTTPException(status_code=400, detail="Malformed server config")
        servers[name]["enabled"] = bool(body.enabled)
        save_config(cfg)
    return {"ok": True, "name": name, "enabled": bool(body.enabled)}


def _merge_mcp_env_on_update(
    existing_env: Dict[str, Any], incoming_env: Dict[str, str]
) -> Dict[str, str]:
    """Merge env updates, preserving secrets when the client echoes redacted values."""
    merged: Dict[str, str] = {}
    prior = {str(k): str(v) for k, v in (existing_env or {}).items()}
    for key, value in (incoming_env or {}).items():
        k = str(key).strip()
        if not k:
            continue
        v = str(value)
        if k in prior:
            redacted = _redact_mcp_env({k: prior[k]}).get(k, "")
            if v in {"", "***", redacted}:
                merged[k] = prior[k]
                continue
        merged[k] = v
    return merged


@router.put("/api/mcp/servers/{name}")
async def update_mcp_server(
    name: str, body: MCPServerCreate, profile: Optional[str] = None
):
    """Update an existing MCP server entry (preserves auto_spawned and enabled flags)."""
    from keprix_cli.mcp_config import _get_mcp_servers, _remove_mcp_server, _save_mcp_server

    with _profile_scope(body.profile or profile):
        servers = _get_mcp_servers()
    if name not in servers:
        raise HTTPException(status_code=404, detail=f"Server '{name}' not found")

    existing = servers[name]
    if not body.url and not body.command:
        raise HTTPException(
            status_code=400,
            detail="Provide either a URL (HTTP/SSE server) or a command (stdio server)",
        )

    server_config: Dict[str, Any] = {}
    if body.url:
        server_config["url"] = body.url.strip()
        if body.transport == "sse":
            server_config["transport"] = "sse"
    if body.command:
        server_config["command"] = body.command.strip()
        server_config["args"] = list(body.args or [])
    elif body.args:
        server_config["args"] = list(body.args)
    if body.env is not None:
        server_config["env"] = _merge_mcp_env_on_update(
            existing.get("env") or {}, dict(body.env)
        )
    if body.auth:
        server_config["auth"] = body.auth
    for flag in ("auto_spawned", "enabled"):
        if flag in existing:
            server_config[flag] = existing[flag]

    new_name = (body.name or name).strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Server name is required")

    try:
        with _profile_scope(body.profile or profile):
            if new_name != name:
                if new_name in servers and new_name != name:
                    raise HTTPException(
                        status_code=409, detail=f"Server '{new_name}' already exists"
                    )
                _remove_mcp_server(name)
            if not _save_mcp_server(new_name, server_config):
                raise HTTPException(
                    status_code=400,
                    detail=f"Server '{new_name}' rejected: suspicious configuration",
                )
    except HTTPException:
        raise
    except Exception as exc:
        _log.exception("PUT /api/mcp/servers/{name} failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _mcp_server_summary(new_name, server_config)


@router.get("/api/mcp/catalog")
async def list_mcp_catalog(profile: Optional[str] = None):
    """Browse the Nous-approved MCP catalog (the optional-mcps/ manifests).

    Each entry reports whether it's already installed and enabled so the UI
    can show install / enabled state inline.  This is the same catalog
    `keprix mcp catalog` / `keprix mcp install` read.  ``profile`` scopes
    the installed/enabled annotations (the catalog itself is repo-shipped
    and identical for every profile).
    """
    try:
        from keprix_cli import mcp_catalog
    except Exception as exc:
        _log.exception("mcp_catalog import failed")
        raise HTTPException(status_code=500, detail=f"Catalog unavailable: {exc}")

    entries = []
    try:
        with _profile_scope(profile):
            catalog_entries = list(mcp_catalog.list_catalog())
            installed_state = {
                e.name: (mcp_catalog.is_installed(e.name), mcp_catalog.is_enabled(e.name))
                for e in catalog_entries
            }
        for entry in catalog_entries:
            auth = entry.auth
            entries.append({
                "name": entry.name,
                "description": entry.description,
                "source": entry.source,
                "transport": entry.transport.type,
                "auth_type": getattr(auth, "type", "none"),
                # Env vars the user must supply (names + prompts only, never values).
                "required_env": [
                    {"name": e.name, "prompt": e.prompt, "required": e.required}
                    for e in getattr(auth, "env", []) or []
                ],
                "needs_install": entry.install is not None,
                "installed": installed_state.get(entry.name, (False, False))[0],
                "enabled": installed_state.get(entry.name, (False, False))[1],
            })
    except HTTPException:
        # Unknown/invalid profile → 404, not a silently-empty catalog.
        raise
    except Exception:
        _log.exception("list_mcp_catalog failed")

    diagnostics = []
    try:
        diagnostics = [
            {"name": n, "kind": k, "message": m}
            for (n, k, m) in mcp_catalog.catalog_diagnostics()
        ]
    except Exception:
        pass

    suggested_catalog: List[Dict[str, Any]] = []
    try:
        from keprix_cli.autonomous_mcp_catalog import get_catalog

        suggested_catalog = get_catalog()
    except Exception:
        _log.exception("autonomous_mcp_catalog import failed")

    return {
        "catalog": suggested_catalog,
        "entries": entries,
        "diagnostics": diagnostics,
    }


class MCPCatalogAddBody(BaseModel):
    name: Optional[str] = None
    env: Dict[str, str] = {}
    vault_env: Dict[str, str] = {}
    profile: Optional[str] = None


@router.post("/api/mcp/catalog/{key}/add")
async def add_mcp_from_catalog(
    key: str,
    body: MCPCatalogAddBody = MCPCatalogAddBody(),
    profile: Optional[str] = None,
    user: Optional[dict] = Depends(_maybe_current_user),
):
    """Add a curated npm MCP catalog entry as a configured server."""
    from keprix_cli.autonomous_mcp_catalog import get_entry
    from keprix_cli.mcp_config import _get_mcp_servers, _save_mcp_server
    from keprix_cli.mcp_vault_resolve import resolve_vault_env

    try:
        entry = get_entry(key)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Catalog entry '{key}' not found")

    name = (body.name if body.name else key).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Server name is required")

    with _profile_scope(body.profile or profile):
        existing = _get_mcp_servers()
    if name in existing:
        raise HTTPException(status_code=409, detail=f"Server '{name}' already exists")

    server_config: Dict[str, Any] = {"auto_spawned": False}
    if entry.get("url"):
        server_config["url"] = entry["url"]
    if entry.get("command"):
        server_config["command"] = entry["command"]
        if entry.get("args"):
            server_config["args"] = list(entry["args"])
    if entry.get("auth_type") == "oauth":
        server_config["auth"] = "oauth"
    env = dict(body.env or {})
    if body.vault_env:
        vault_values = await resolve_vault_env(body.vault_env, user)
        env.update(vault_values)
    required_env = list(entry.get("required_env") or [])
    if required_env:
        missing = [k for k in required_env if not str(env.get(k, "")).strip()]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required credentials: {', '.join(missing)}",
            )
        server_config["env"] = env
    elif env:
        server_config["env"] = env

    try:
        with _profile_scope(body.profile or profile):
            if not _save_mcp_server(name, server_config):
                raise HTTPException(
                    status_code=400,
                    detail=f"Server '{name}' rejected: suspicious configuration",
                )
    except HTTPException:
        raise
    except Exception as exc:
        _log.exception("POST /api/mcp/catalog/{key}/add failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _mcp_server_summary(name, server_config)


@router.get("/api/mcp/auto-spawn/status")
async def get_auto_spawn_status(profile: Optional[str] = None):
    """Return whether auto-spawn is enabled and auto-spawned server names."""
    from keprix_cli.mcp_config import _get_mcp_servers
    from keprix_cli.mcp_spawn_settings import is_auto_mcp_spawn_enabled

    env_raw = os.environ.get("KEPRIX_AUTO_MCP_SPAWN")
    env_locked = env_raw is not None and str(env_raw).strip() != ""
    with _profile_scope(profile):
        servers = _get_mcp_servers()
    auto_spawned = [
        name for name, cfg in servers.items() if cfg.get("auto_spawned") is True
    ]
    return {
        "enabled": is_auto_mcp_spawn_enabled(),
        "auto_spawned_servers": auto_spawned,
        "env_locked": env_locked,
        "source": "env" if env_locked else "config",
    }


class AutoSpawnSettingsBody(BaseModel):
    enabled: bool


@router.put("/api/mcp/auto-spawn/settings")
async def update_auto_spawn_settings(body: AutoSpawnSettingsBody):
    """Toggle autonomous MCP spawn (persisted in config.yaml unless env overrides)."""
    from keprix_cli.mcp_config import _get_mcp_servers
    from keprix_cli.mcp_spawn_settings import is_auto_mcp_spawn_enabled, set_auto_mcp_spawn_enabled

    env_raw = os.environ.get("KEPRIX_AUTO_MCP_SPAWN")
    if env_raw is not None and str(env_raw).strip() != "":
        raise HTTPException(
            status_code=400,
            detail=(
                "KEPRIX_AUTO_MCP_SPAWN is set in the environment and overrides config. "
                "Unset that variable to control auto-spawn from the UI."
            ),
        )
    set_auto_mcp_spawn_enabled(body.enabled)
    with _profile_scope(None):
        servers = _get_mcp_servers()
    auto_spawned = [
        name for name, cfg in servers.items() if cfg.get("auto_spawned") is True
    ]
    return {
        "enabled": is_auto_mcp_spawn_enabled(),
        "auto_spawned_servers": auto_spawned,
        "env_locked": False,
        "source": "config",
    }


@router.delete("/api/mcp/auto-spawn/{name}")
async def remove_auto_spawned_server(name: str, profile: Optional[str] = None):
    """Remove an auto-spawned MCP server from config and the live session."""
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

    try:
        from tools.mcp_tool import unregister_server_runtime

        unregister_server_runtime(name)
    except Exception:
        pass

    with _profile_scope(profile):
        _remove_mcp_server(name)

    return {"ok": True}


class MCPCatalogInstall(BaseModel):
    name: str
    # env: KEY=VALUE map for catalog entries that declare required env vars.
    env: Dict[str, str] = {}
    enable: bool = True
    profile: Optional[str] = None


@router.post("/api/mcp/catalog/install")
async def install_mcp_catalog_entry(body: MCPCatalogInstall, profile: Optional[str] = None):
    """Install a catalog MCP into config.yaml.

    For HTTP/stdio entries with required env vars, those are written to .env
    via the standard env path so the agent can read them at session start.
    Entries that need a git bootstrap (``needs_install``) are installed via
    the CLI action path because the clone can take time.
    """
    from keprix_cli import mcp_catalog

    name = (body.name or "").strip()
    entry = mcp_catalog.get_entry(name)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"No catalog entry '{name}'")

    # Persist any supplied env vars first (catalog entries declare which names
    # they need; we only write the ones the user provided).
    effective_profile = body.profile or profile
    if body.env:
        with _profile_scope(effective_profile):
            for k, v in body.env.items():
                if v:
                    save_env_value(k, v)

    # Git-bootstrap entries can take a while to clone — run via the background
    # action path so the request returns immediately and the UI can tail logs.
    # The -p subprocess rebinds KEPRIX_HOME-derived paths in the child.
    if entry.install is not None:
        try:
            from keprix_cli.web_server import _spawn_keprix_action, _profile_cli_args
            proc = _spawn_keprix_action(
                _profile_cli_args(effective_profile) + ["mcp", "install", name],
                "mcp-install",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Install failed: {exc}")
        return {"ok": True, "name": name, "background": True, "action": "mcp-install"}

    # No git step — install synchronously via the catalog API. install_entry
    # routes through load_config/save_config + save_env_value, all call-time
    # resolvers, so the context override scopes it. Wrap the to_thread body
    # in the scope INSIDE the thread (contextvars don't propagate into
    # to_thread the other way around — asyncio.to_thread copies context, so
    # setting it here works; keep it explicit for clarity).
    def _install_scoped():
        with _profile_scope(effective_profile):
            mcp_catalog.install_entry(entry, enable=body.enable)

    try:
        await asyncio.to_thread(_install_scoped)
    except HTTPException:
        raise
    except Exception as exc:
        _log.exception("install_mcp_catalog_entry failed")
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "name": name, "background": False}


# Register mcp-install action log path when dashboard action helpers exist.
try:
    from keprix_cli import web_server as _ws

    _ws._ACTION_LOG_FILES.setdefault("mcp-install", "action-mcp-install.log")
except Exception:
    pass
