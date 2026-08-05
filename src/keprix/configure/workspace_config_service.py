"""Conversational workspace preferences (durable)."""

from __future__ import annotations

from typing import Any

from keprix.configure.workspace_settings_store import (
    CONVERSATIONAL_KEYS,
    load_workspace_settings,
    public_workspace_settings,
    save_workspace_settings,
)

_WORKSPACE_FIELDS = (
    {
        "key": "timezone",
        "label": "Timezone",
        "description": "IANA timezone (e.g. Europe/London, America/New_York).",
        "sensitive": False,
        "example": "Europe/London",
    },
    {
        "key": "language",
        "label": "Language",
        "description": "UI / reply language code.",
        "sensitive": False,
        "example": "en",
    },
    {
        "key": "instance_name",
        "label": "Instance name",
        "description": "Display name for this Keprix instance.",
        "sensitive": False,
        "example": "Keprix",
    },
    {
        "key": "instance_url",
        "label": "Instance URL",
        "description": "Public base URL for webhooks and companion pairing.",
        "sensitive": False,
        "example": "https://keprix.example.com",
    },
    {
        "key": "quiet_hours_enabled",
        "label": "Quiet hours enabled",
        "description": "true/false to enable quiet hours.",
        "sensitive": False,
        "example": "true",
    },
    {
        "key": "quiet_hours_start",
        "label": "Quiet hours start",
        "description": "HH:MM local start (24h).",
        "sensitive": False,
        "example": "22:00",
    },
    {
        "key": "quiet_hours_end",
        "label": "Quiet hours end",
        "description": "HH:MM local end (24h).",
        "sensitive": False,
        "example": "07:00",
    },
)

_SESSIONS: dict[str, dict[str, Any]] = {}


def list_workspace_payload() -> dict[str, Any]:
    return {"settings": public_workspace_settings(), "all": load_workspace_settings()}


def requirements_payload(field: str | None = None) -> dict[str, Any]:
    if field:
        match = next((f for f in _WORKSPACE_FIELDS if f["key"] == field), None)
        if match is None:
            return {"ok": False, "error": f"Unknown field: {field}"}
        return {"ok": True, "field": match, "next_field": match}
    return {
        "ok": True,
        "fields": list(_WORKSPACE_FIELDS),
        "next_field": _WORKSPACE_FIELDS[0],
        "hint": "Use collect with one field at a time, or configure with a settings object.",
    }


def configure_workspace(settings: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in (settings or {}).items():
        if key not in CONVERSATIONAL_KEYS and key not in load_workspace_settings():
            continue
        if key == "quiet_hours_enabled":
            cleaned[key] = str(value).strip().lower() in {"1", "true", "yes", "on"}
        else:
            cleaned[key] = value
    if not cleaned:
        return {"ok": False, "error": "No recognized settings fields provided"}
    saved = save_workspace_settings(cleaned)
    return {
        "ok": True,
        "settings": {k: saved.get(k) for k in cleaned},
        "message": "Workspace preferences saved to ~/.keprix/workspace_settings.json.",
    }


def collect_workspace(
    credentials: dict[str, Any] | None = None,
    *,
    session_id: str = "default",
    field: str | None = None,
) -> dict[str, Any]:
    """Collect one preference field; save when a value is provided for the target field."""
    sess = _SESSIONS.setdefault(session_id, {})
    incoming = {str(k): v for k, v in (credentials or {}).items() if v is not None}
    target = field or (next(iter(incoming.keys())) if incoming else "timezone")
    meta = next((f for f in _WORKSPACE_FIELDS if f["key"] == target), None)
    if meta is None:
        return {"ok": False, "error": f"Unknown field: {target}"}

    if target in incoming:
        result = configure_workspace({target: incoming[target]})
        sess[target] = incoming[target]
        result["complete"] = True
        result["field"] = target
        return result

    return {
        "ok": True,
        "complete": False,
        "next_field": {
            **meta,
            "ask": f"Please send your {meta['label']} (example: {meta.get('example')}).",
        },
        "message": f"Let's set {meta['label']}.",
        "collected_field_keys": sorted(str(k) for k in sess.keys()),
    }
