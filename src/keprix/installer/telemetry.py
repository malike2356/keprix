"""Opt-in anonymous install telemetry."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _telemetry_path() -> Path:
    path = Path.home() / ".keprix" / "installer" / "telemetry.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def telemetry_enabled() -> bool:
    return os.environ.get("KEPRIX_INSTALL_TELEMETRY", "").strip().lower() in {"1", "true", "yes"}


def build_telemetry_payload(event: str, **fields: Any) -> dict[str, Any]:
    return {
        "event": event,
        "install_id": os.environ.get("KEPRIX_INSTALL_ID") or str(uuid.uuid4())[:12],
        "at": datetime.now(timezone.utc).isoformat(),
        "platform": fields.get("platform"),
        "success": fields.get("success"),
        "step": fields.get("step"),
    }


def record_telemetry(event: str, **fields: Any) -> dict[str, Any] | None:
    if not telemetry_enabled():
        return None
    payload = build_telemetry_payload(event, **fields)
    with _telemetry_path().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
    return payload
