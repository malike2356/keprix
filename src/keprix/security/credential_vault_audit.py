"""Credential vault audit helpers for security operations."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from keprix_cli.config import get_keprix_home
from keprix.providers.ops.credential_health import CredentialHealth, CredentialStatus


def _rotation_state_path() -> Path:
    return get_keprix_home() / "security" / "credential_rotation.json"


def _load_rotation_state() -> dict[str, Any]:
    path = _rotation_state_path()
    if not path.exists():
        return {"credentials": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"credentials": {}}


def audit_credentials(
    *,
    expiring_days: int | None = None,
    rotation_due: bool = False,
) -> dict[str, Any]:
    health = CredentialHealth()
    results = health.check_all()
    now = datetime.now(timezone.utc)
    rotation = _load_rotation_state().get("credentials") or {}

    rows: list[dict[str, Any]] = []
    for item in results:
        row = {
            "provider": item.provider,
            "status": item.status.value,
            "env_var": item.env_var,
            "detail": item.detail,
        }
        rotated_at = rotation.get(item.provider, {}).get("last_rotated_at")
        if rotated_at:
            try:
                rotated = datetime.fromisoformat(str(rotated_at).replace("Z", "+00:00"))
                age_days = (now - rotated).days
                row["days_since_rotation"] = age_days
                row["rotation_due"] = age_days >= 90
            except Exception:
                row["rotation_due"] = True
        else:
            row["rotation_due"] = True

        if expiring_days is not None:
            row["expiring_within_days"] = expiring_days if item.status != CredentialStatus.OK else None
        rows.append(row)

    if rotation_due:
        rows = [row for row in rows if row.get("rotation_due")]
    if expiring_days is not None:
        rows = [
            row
            for row in rows
            if row.get("status") != CredentialStatus.OK.value
            or row.get("rotation_due")
        ]

    issues = [row for row in rows if row.get("status") != CredentialStatus.OK.value or row.get("rotation_due")]
    return {
        "checked_at": now.isoformat().replace("+00:00", "Z"),
        "credentials": rows,
        "issue_count": len(issues),
        "ok": len(issues) == 0,
    }
