"""BotFather-style collect sessions for provider API keys."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.channels.sensitive_scrub import sensitive_field_warning
from keprix.configure.provider_requirements import (
    ConfigField,
    ProviderRequirement,
    find_provider_by_alias,
    get_optional_fields,
    get_provider,
    get_required_fields,
    validate_provider_credentials,
)
from keprix.proxy.paths import keprix_home

_LOCK = threading.RLock()


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sessions_path() -> Path:
    return keprix_home() / "provider_setup_sessions.json"


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


def _session_key(provider_id: str, session_id: str | None) -> str:
    sid = (session_id or "default").strip() or "default"
    return f"{sid}::{provider_id}"


def _map_field_key(req: ProviderRequirement, raw_key: str) -> str | None:
    for fld in req.fields:
        if fld.key == raw_key or fld.env_key == raw_key:
            return fld.key
    return None


def _next_missing(provider_id: str, collected: dict[str, str]) -> ConfigField | None:
    for fld in get_required_fields(provider_id):
        if not collected.get(fld.key):
            return fld
    return None


def _field_payload(fld: ConfigField) -> dict[str, Any]:
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


def collect_provider_field(
    provider_id: str,
    *,
    credentials: dict[str, str] | None = None,
    session_id: str | None = None,
    include_optional: bool = False,
) -> dict[str, Any]:
    req = get_provider(provider_id) or find_provider_by_alias(provider_id)
    if req is None:
        return {"ok": False, "error": f"Unknown provider: {provider_id}"}

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
            "provider_id": req.id,
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
            if fld.key not in collected:
                next_fld = fld
                break

    # For ollama with no required fields, prompt host once if nothing collected yet
    if next_fld is None and req.id == "ollama" and not collected and not incoming:
        opt = get_optional_fields(req.id)
        if opt:
            next_fld = opt[0]

    if next_fld is not None:
        return {
            "ok": True,
            "complete": False,
            "provider_id": req.id,
            "name": req.name,
            "collected_field_keys": sorted(collected.keys()),
            "next_field": _field_payload(next_fld),
            "message": (
                ("Got it." if incoming else f"Let's configure {req.name}.")
                + f" Next: {next_fld.label}."
            ),
        }

    ok, message, cleaned = validate_provider_credentials(req.id, collected)
    if not ok:
        return {
            "ok": False,
            "complete": False,
            "provider_id": req.id,
            "error": message,
            "collected_field_keys": sorted(collected.keys()),
        }

    return {
        "ok": True,
        "complete": True,
        "provider_id": req.id,
        "name": req.name,
        "collected_field_keys": sorted(cleaned.keys()),
        "credentials": cleaned,
        "message": f"All required fields for {req.name} collected. Saving.",
        "session_key": key,
    }


def clear_provider_session(provider_id: str, session_id: str | None = None) -> None:
    req = get_provider(provider_id) or find_provider_by_alias(provider_id)
    if req is None:
        return
    key = _session_key(req.id, session_id)
    with _LOCK:
        data = _load()
        (data.setdefault("sessions", {})).pop(key, None)
        _save(data)
