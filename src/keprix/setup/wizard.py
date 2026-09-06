"""First-run setup wizard state."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir


def _marker_path() -> Path:
    return Path(data_dir()) / ".setup_complete"


def is_setup_complete() -> bool:
    env = os.environ.get("KEPRIX_SETUP_COMPLETE", "").strip().lower()
    if env in {"1", "true", "yes"}:
        return True
    return _marker_path().exists()


def is_public_setup_disabled() -> bool:
    """True on a deployment that's reachable by the public but is not an
    offering of hosted, multi-tenant access - e.g. the maintainer's own
    keprixai.com/app.keprixai.com marketing/demo instance. Keprix Community
    is self-hosted software: this instance already has its one owner, and
    the setup wizard (which creates THE owner account for whichever
    instance serves it) must never be presented to - or usable by - an
    anonymous visitor there. Every other self-hosted install leaves this
    unset and keeps the normal first-run wizard behavior."""
    env = os.environ.get("KEPRIX_PUBLIC_SETUP_DISABLED", "").strip().lower()
    return env in {"1", "true", "yes"}


def mark_setup_complete(*, owner_email: str | None = None) -> dict[str, Any]:
    base = Path(data_dir())
    base.mkdir(parents=True, exist_ok=True)
    payload = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "owner_email": owner_email,
    }
    _marker_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def wizard_status() -> dict[str, Any]:
    return {"complete": is_setup_complete(), "public_setup_disabled": is_public_setup_disabled()}


def credential_management_options() -> list[dict[str, Any]]:
    return [
        {"id": "external_vault", "label": "External vault", "recommended": True, "legacy": False},
        {"id": "cordon", "label": "Cordon proxy", "recommended": False, "legacy": False},
        {"id": "keprix_vault", "label": "Keprix encrypted vault", "recommended": False, "legacy": True},
        {"id": "env", "label": "Plain environment variables", "recommended": False, "legacy": True},
    ]
