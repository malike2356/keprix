"""In-progress BotFather-style channel setup sessions (one field at a time)."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.channels.channel_requirements import (
    ChannelField,
    ChannelRequirement,
    find_channel_by_alias,
    get_channel,
    get_optional_fields,
    get_required_fields,
    validate_credentials,
)
from keprix.channels.sensitive_scrub import sensitive_field_warning
from keprix.proxy.paths import keprix_home

_LOCK = threading.RLock()


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sessions_path() -> Path:
    return keprix_home() / "channel_setup_sessions.json"


def _load() -> dict[str, Any]:
    path = sessions_path()
    if not path.is_file():
        return {"sessions": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"sessions": {}}
    if not isinstance(data, dict):
        return {"sessions": {}}
    data.setdefault("sessions", {})
    return data


def _save(data: dict[str, Any]) -> None:
    path = sessions_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _session_key(channel_id: str, session_id: str | None) -> str:
    sid = (session_id or "default").strip() or "default"
    return f"{sid}::{channel_id}"


def _map_field_key(req: ChannelRequirement, raw_key: str) -> str | None:
    for fld in req.fields:
        if fld.key == raw_key or fld.env_key == raw_key:
            return fld.key
    return None


def _next_missing(channel_id: str, collected: dict[str, str]) -> ChannelField | None:
    req = get_channel(channel_id)
    if req is None:
        return None
    for fld in get_required_fields(channel_id):
        if not collected.get(fld.key):
            return fld
    if channel_id == "matrix":
        if not collected.get("access_token") and not collected.get("password"):
            for fld in req.fields:
                if fld.key == "access_token":
                    return fld
    return None


def _field_payload(fld: ChannelField) -> dict[str, Any]:
    payload = {
        "key": fld.key,
        "label": fld.label,
        "description": fld.description,
        "sensitive": fld.sensitive,
        "optional": fld.optional,
        "example": fld.example,
        "ask": f"Please send your {fld.label}.",
    }
    if fld.sensitive:
        payload["ask"] = sensitive_field_warning(field_label=fld.label)
        payload["voice_warning"] = True
    return payload


def collect_field(
    channel_id: str,
    *,
    credentials: dict[str, str] | None = None,
    session_id: str | None = None,
    include_optional: bool = False,
) -> dict[str, Any]:
    """Start or continue a one-field-at-a-time setup session."""
    req = get_channel(channel_id) or find_channel_by_alias(channel_id)
    if req is None:
        return {"ok": False, "error": f"Unknown channel: {channel_id}"}

    key = _session_key(req.id, session_id)
    incoming = {
        str(k): str(v).strip()
        for k, v in (credentials or {}).items()
        if v is not None and str(v).strip()
    }

    with _LOCK:
        data = _load()
        sessions = data.setdefault("sessions", {})
        sess = sessions.get(key) or {
            "channel_id": req.id,
            "collected": {},
            "created_at": _utcnow(),
        }
        collected = dict(sess.get("collected") or {})
        for fk, fv in incoming.items():
            mapped = _map_field_key(req, fk)
            if mapped is None:
                return {"ok": False, "error": f"Unknown field '{fk}' for {req.name}"}
            collected[mapped] = fv

        sess["collected"] = collected
        sess["updated_at"] = _utcnow()
        sessions[key] = sess
        _save(data)

    next_fld = _next_missing(req.id, collected)
    if next_fld is None and include_optional:
        for fld in get_optional_fields(req.id):
            if fld.key in collected:
                continue
            if req.id == "matrix" and fld.key in {"access_token", "password"}:
                continue
            next_fld = fld
            break

    if next_fld is not None:
        return {
            "ok": True,
            "complete": False,
            "channel_id": req.id,
            "name": req.name,
            "collected_field_keys": sorted(collected.keys()),
            "received_count": len(incoming),
            "next_field": _field_payload(next_fld),
            "message": (
                ("Got it." if incoming else f"Let's configure {req.name}.")
                + f" Next: {next_fld.label}."
            ),
        }

    ok, message, cleaned = validate_credentials(req.id, collected)
    if not ok:
        return {
            "ok": False,
            "complete": False,
            "channel_id": req.id,
            "error": message,
            "collected_field_keys": sorted(collected.keys()),
        }

    return {
        "ok": True,
        "complete": True,
        "channel_id": req.id,
        "name": req.name,
        "collected_field_keys": sorted(cleaned.keys()),
        "credentials": cleaned,
        "message": f"All required fields for {req.name} collected. Saving and testing.",
        "session_key": key,
    }


def clear_session(channel_id: str, session_id: str | None = None) -> None:
    req = get_channel(channel_id) or find_channel_by_alias(channel_id)
    if req is None:
        return
    key = _session_key(req.id, session_id)
    with _LOCK:
        data = _load()
        sessions = data.setdefault("sessions", {})
        sessions.pop(key, None)
        _save(data)


def peek_collected(channel_id: str, session_id: str | None = None) -> dict[str, str]:
    req = get_channel(channel_id) or find_channel_by_alias(channel_id)
    if req is None:
        return {}
    key = _session_key(req.id, session_id)
    with _LOCK:
        data = _load()
        sess = (data.get("sessions") or {}).get(key) or {}
    return dict(sess.get("collected") or {})
