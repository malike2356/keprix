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
    return {"complete": is_setup_complete()}
