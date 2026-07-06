"""Admin web search provider discovery, persistence, and tests."""

from __future__ import annotations

from typing import Any

from keprix.api.provider_settings import persist_env_value, remove_env_value


def _env_configured(key: str) -> bool:
    try:
        from keprix_cli.config import get_env_value

        value = get_env_value(key)
    except Exception:
        value = None
    if value is None:
        import os

        value = os.getenv(key, "")
    return bool(str(value or "").strip())


def _load_web_config() -> dict[str, Any]:
    try:
        from keprix_cli.config import load_config

        web = load_config().get("web", {})
        return web if isinstance(web, dict) else {}
    except Exception:
        return {}


def _active_search_backend() -> str:
    web = _load_web_config()
    specific = str(web.get("search_backend") or "").strip().lower()
    if specific:
        return specific
    return str(web.get("backend") or "").strip().lower()


def _set_active_search_backend(backend_id: str) -> None:
    from keprix_cli.config import load_config, save_config

    cfg = load_config()
    web = cfg.setdefault("web", {})
    if not isinstance(web, dict):
        web = {}
        cfg["web"] = web
    web["search_backend"] = backend_id.strip().lower()
    save_config(cfg)


def _discover_provider_rows() -> list[dict[str, Any]]:
    try:
        from agent.web_search_registry import list_providers as list_web_providers
        from keprix_cli.plugins import _ensure_plugins_discovered

        _ensure_plugins_discovered()
        providers = list_web_providers()
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    for provider in providers:
        name = getattr(provider, "name", None)
        if not name or not getattr(provider, "supports_search", lambda: False)():
            continue
        try:
            schema = provider.get_setup_schema()
        except Exception:
            continue
        if not isinstance(schema, dict):
            continue
        env_vars = []
        for item in schema.get("env_vars", []) or []:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            env_vars.append(
                {
                    "key": key,
                    "prompt": str(item.get("prompt") or key),
                    "url": str(item.get("url") or ""),
                    "secret": key.endswith(("_API_KEY", "_TOKEN", "_SECRET", "_PASS")),
                }
            )
        rows.append(
            {
                "id": str(name),
                "label": str(schema.get("name") or getattr(provider, "display_name", name)),
                "badge": str(schema.get("badge") or ""),
                "description": str(schema.get("tag") or ""),
                "env_vars": env_vars,
            }
        )
    rows.sort(key=lambda row: (row["id"] != "tavily", row["label"].lower()))
    return rows


def web_search_provider_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": row["id"],
            "label": row["label"],
            "badge": row["badge"],
            "description": row["description"],
            "env_vars": row["env_vars"],
        }
        for row in _discover_provider_rows()
    ]


def _provider_row(provider_id: str) -> dict[str, Any] | None:
    for row in _discover_provider_rows():
        if row["id"] == provider_id:
            return row
    return None


def _provider_connected(provider_id: str) -> bool:
    row = _provider_row(provider_id)
    if row is None:
        return False
    env_vars = row.get("env_vars") or []
    if not env_vars:
        try:
            from agent.web_search_registry import get_provider

            provider = get_provider(provider_id)
            return bool(provider and provider.is_available())
        except Exception:
            return False
    return all(_env_configured(str(item["key"])) for item in env_vars)


def web_search_settings_snapshot() -> dict[str, Any]:
    active = _active_search_backend()
    providers: dict[str, dict[str, Any]] = {}
    for row in _discover_provider_rows():
        provider_id = row["id"]
        connected = _provider_connected(provider_id)
        providers[provider_id] = {
            "connected": connected,
            "is_active": provider_id == active,
        }
    if active and active not in providers:
        providers[active] = {"connected": _provider_connected(active), "is_active": True}
    return {
        "active_backend": active or None,
        "providers": providers,
        "catalog": web_search_provider_catalog(),
    }


def save_web_search_settings(
    provider_id: str,
    *,
    env_values: dict[str, str] | None = None,
    set_active: bool = True,
) -> dict[str, Any]:
    row = _provider_row(provider_id)
    if row is None:
        raise KeyError(provider_id)

    values = {str(k): str(v) for k, v in (env_values or {}).items() if str(v).strip()}
    allowed_keys = {str(item["key"]) for item in row.get("env_vars") or []}
    for key, value in values.items():
        if key not in allowed_keys:
            raise ValueError(f"Unsupported setting: {key}")
        persist_env_value(key, value.strip())

    if set_active:
        _set_active_search_backend(provider_id)

    snapshot = web_search_settings_snapshot()
    return snapshot["providers"].get(provider_id, {"connected": False, "is_active": set_active})


def delete_web_search_settings(provider_id: str) -> dict[str, Any]:
    row = _provider_row(provider_id)
    if row is None:
        raise KeyError(provider_id)

    for item in row.get("env_vars") or []:
        remove_env_value(str(item["key"]))

    active = _active_search_backend()
    if active == provider_id:
        from keprix_cli.config import load_config, save_config

        cfg = load_config()
        web = cfg.setdefault("web", {})
        if isinstance(web, dict):
            web["search_backend"] = ""
        save_config(cfg)

    snapshot = web_search_settings_snapshot()
    return snapshot["providers"].get(provider_id, {"connected": False, "is_active": False})


def activate_web_search_backend(provider_id: str) -> dict[str, Any]:
    row = _provider_row(provider_id)
    if row is None:
        raise KeyError(provider_id)
    if not _provider_connected(provider_id):
        raise ValueError(f"Configure {row['label']} before activating it for research.")
    _set_active_search_backend(provider_id)
    return web_search_settings_snapshot()


def test_web_search_settings(provider_id: str) -> dict[str, Any]:
    row = _provider_row(provider_id)
    if row is None:
        return {"ok": False, "message": "Provider not found"}
    if not _provider_connected(provider_id):
        return {"ok": False, "message": "Not configured"}

    try:
        from agent.web_search_registry import get_provider

        provider = get_provider(provider_id)
        if provider is None or not provider.supports_search():
            return {"ok": False, "message": "Search provider unavailable"}
        result = provider.search("keprix connectivity test", limit=1)
        if result.get("success"):
            count = len(result.get("data", {}).get("web", []))
            return {
                "ok": True,
                "message": f"{row['label']} connected ({count} result{'s' if count != 1 else ''})",
            }
        return {"ok": False, "message": str(result.get("error") or "Search test failed")}
    except Exception as exc:
        return {"ok": False, "message": str(exc)}
