"""Encrypted channel configuration store + .env upsert for Keprix."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.channels.channel_requirements import (
    credentials_to_env,
    get_channel,
    validate_credentials,
)
from keprix.email.crypto import decrypt_secret, encrypt_secret
from keprix.proxy.paths import keprix_home


_LOCK = threading.RLock()


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def store_path() -> Path:
    override = os.environ.get("KEPRIX_CHANNEL_CONFIG_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return keprix_home() / "channel_configurations.json"


def env_path() -> Path:
    override = os.environ.get("KEPRIX_ENV_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return keprix_home() / ".env"


def _ensure_encryption_key() -> None:
    """Prefer ENCRYPTION_KEY; otherwise bootstrap a local key file under KEPRIX_HOME."""
    if os.environ.get("ENCRYPTION_KEY", "").strip():
        return
    key_file = keprix_home() / ".channel_config_key"
    if key_file.is_file():
        os.environ["ENCRYPTION_KEY"] = key_file.read_text(encoding="utf-8").strip()
        return
    import secrets

    keprix_home().mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    key_file.write_text(token, encoding="utf-8")
    try:
        key_file.chmod(0o600)
    except OSError:
        pass
    os.environ["ENCRYPTION_KEY"] = token


def _load_raw() -> dict[str, Any]:
    path = store_path()
    if not path.is_file():
        return {"channels": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"channels": {}}
    if not isinstance(data, dict):
        return {"channels": {}}
    channels = data.get("channels")
    if not isinstance(channels, dict):
        data["channels"] = {}
    return data


def _save_raw(data: dict[str, Any]) -> None:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _encrypt_credentials(credentials: dict[str, str]) -> str:
    _ensure_encryption_key()
    return encrypt_secret(json.dumps(credentials, sort_keys=True))


def _decrypt_credentials(blob: str) -> dict[str, str]:
    if not blob:
        return {}
    _ensure_encryption_key()
    raw = decrypt_secret(blob)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if v is not None}


def read_env_file(path: Path | None = None) -> dict[str, str]:
    target = path or env_path()
    existing: dict[str, str] = {}
    if not target.is_file():
        return existing
    for line in target.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        existing[key.strip()] = value.strip()
    return existing


def upsert_env(values: dict[str, str], path: Path | None = None) -> Path:
    """Merge values into ~/.keprix/.env and os.environ."""
    target = path or env_path()
    existing = read_env_file(target)
    merged = {**existing, **{k: v for k, v in values.items() if v is not None}}
    lines = [f"{key}={value}" for key, value in sorted(merged.items())]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        target.chmod(0o600)
    except OSError:
        pass
    for key, value in values.items():
        if value is not None:
            os.environ[key] = value
    return target


def remove_env_keys(keys: list[str], path: Path | None = None) -> Path:
    target = path or env_path()
    existing = read_env_file(target)
    for key in keys:
        existing.pop(key, None)
        os.environ.pop(key, None)
    lines = [f"{key}={value}" for key, value in sorted(existing.items())]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(("\n".join(lines) + "\n") if lines else "", encoding="utf-8")
    return target


def list_configurations(*, include_secrets: bool = False) -> list[dict[str, Any]]:
    """Return channel rows merged with registry (never include secrets by default)."""
    with _LOCK:
        raw = _load_raw()
        stored = raw.get("channels") or {}

    from keprix.channels.channel_requirements import CHANNEL_REQUIREMENTS

    rows: list[dict[str, Any]] = []
    for req in CHANNEL_REQUIREMENTS:
        row = stored.get(req.id) or {}
        configured = bool(row.get("credentials_enc"))
        item: dict[str, Any] = {
            "id": req.id,
            "name": req.name,
            "status": row.get("status") or ("configured" if configured else "not_configured"),
            "configured": configured,
            "requires_restart": bool(
                row.get("requires_restart", req.requires_restart) if configured else False
            ),
            "tested_at": row.get("tested_at"),
            "last_error": row.get("last_error"),
            "updated_at": row.get("updated_at"),
            "meta": row.get("meta") or {},
        }
        if include_secrets and configured:
            item["credentials"] = _decrypt_credentials(str(row.get("credentials_enc") or ""))
        rows.append(item)
    return rows


def get_configuration(channel_id: str, *, include_secrets: bool = False) -> dict[str, Any] | None:
    req = get_channel(channel_id)
    if req is None:
        return None
    rows = {r["id"]: r for r in list_configurations(include_secrets=include_secrets)}
    return rows.get(req.id)


def get_decrypted_credentials(channel_id: str) -> dict[str, str]:
    req = get_channel(channel_id)
    if req is None:
        return {}
    with _LOCK:
        raw = _load_raw()
        row = (raw.get("channels") or {}).get(req.id) or {}
    return _decrypt_credentials(str(row.get("credentials_enc") or ""))


def save_configuration(
    channel_id: str,
    credentials: dict[str, str],
    *,
    meta: dict[str, Any] | None = None,
    status: str = "configured",
    last_error: str | None = None,
    tested_at: str | None = None,
) -> dict[str, Any]:
    """Validate, encrypt, persist, and upsert env vars for a channel."""
    from keprix.channels.channel_requirements import find_channel_by_alias

    req = get_channel(channel_id) or find_channel_by_alias(channel_id)
    if req is None:
        raise ValueError(f"Unknown channel: {channel_id}")

    ok, message, cleaned = validate_credentials(req.id, credentials)
    if not ok:
        raise ValueError(message)

    now = _utcnow()
    env_values = credentials_to_env(req.id, cleaned)
    blob = _encrypt_credentials(cleaned)

    with _LOCK:
        raw = _load_raw()
        channels = raw.setdefault("channels", {})
        prev = channels.get(req.id) or {}
        channels[req.id] = {
            "credentials_enc": blob,
            "status": status,
            "requires_restart": req.requires_restart,
            "last_error": last_error,
            "tested_at": tested_at if tested_at is not None else prev.get("tested_at"),
            "created_at": prev.get("created_at") or now,
            "updated_at": now,
            "meta": {**(prev.get("meta") or {}), **(meta or {})},
        }
        _save_raw(raw)

    if env_values:
        upsert_env(env_values)

    from keprix.channels.channel_activation import request_channel_reload

    activation = request_channel_reload(req.id, env_keys=sorted(env_values.keys()))
    requires_restart = bool(activation.get("requires_restart", req.requires_restart))

    with _LOCK:
        raw = _load_raw()
        channels = raw.setdefault("channels", {})
        if req.id in channels:
            channels[req.id]["requires_restart"] = requires_restart
            _save_raw(raw)

    return {
        "id": req.id,
        "name": req.name,
        "status": status,
        "configured": True,
        "requires_restart": requires_restart,
        "tested_at": tested_at,
        "updated_at": now,
        "env_keys_written": sorted(env_values.keys()),
        "restart_hint": activation.get("restart_hint"),
        "activation": {
            "dotenv_reloaded": activation.get("dotenv_reloaded"),
            "gateway_running": activation.get("gateway_running"),
        },
    }


def update_test_result(
    channel_id: str,
    *,
    success: bool,
    message: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    req = get_channel(channel_id)
    if req is None:
        raise ValueError(f"Unknown channel: {channel_id}")
    now = _utcnow()
    with _LOCK:
        raw = _load_raw()
        channels = raw.setdefault("channels", {})
        row = channels.get(req.id)
        if not row:
            raise ValueError(f"{req.name} is not configured")
        row["tested_at"] = now
        row["updated_at"] = now
        row["last_error"] = None if success else message
        row["status"] = "configured" if success else "error"
        if meta:
            row["meta"] = {**(row.get("meta") or {}), **meta}
        _save_raw(raw)
    return get_configuration(req.id) or {}


def remove_configuration(channel_id: str) -> dict[str, Any]:
    from keprix.channels.channel_requirements import find_channel_by_alias

    req = get_channel(channel_id) or find_channel_by_alias(channel_id)
    if req is None:
        raise ValueError(f"Unknown channel: {channel_id}")

    env_keys = [f.env_key for f in req.fields if f.env_key]
    with _LOCK:
        raw = _load_raw()
        channels = raw.setdefault("channels", {})
        existed = req.id in channels
        channels.pop(req.id, None)
        _save_raw(raw)

    if env_keys:
        remove_env_keys([k for k in env_keys if k])

    return {"id": req.id, "removed": existed, "ok": True}
