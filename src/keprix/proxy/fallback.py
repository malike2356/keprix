"""Emergency fallback to the legacy local vault."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.proxy.paths import fallback_state_path, local_vault_path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def enable_fallback(*, hours: int = 24) -> dict[str, Any]:
    expires = _now() + timedelta(hours=hours)
    payload = {"enabled": True, "enabled_at": _now().isoformat(), "expires_at": expires.isoformat(), "severity": "critical"}
    path = fallback_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def disable_fallback() -> dict[str, Any]:
    path = fallback_state_path()
    path.unlink(missing_ok=True)
    return {"enabled": False}


def fallback_status() -> dict[str, Any]:
    path = fallback_state_path()
    if not path.is_file():
        return {"enabled": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"enabled": False}
    expires_at = datetime.fromisoformat(payload["expires_at"])
    if expires_at <= _now():
        disable_fallback()
        return {"enabled": False, "expired": True}
    return payload


def fallback_secret(secret_ref: str) -> str | None:
    if not fallback_status().get("enabled"):
        return None
    path = local_vault_path()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("secrets", {}).get(secret_ref)
    except json.JSONDecodeError:
        return None
