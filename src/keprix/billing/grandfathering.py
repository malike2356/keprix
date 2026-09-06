"""Permanent, admin-controlled workspace feature exemptions."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FEATURES = {"outreach", "property", "business_lines"}


def _path() -> Path:
    root = Path(os.environ.get("KEPRIX_HOME", Path.home() / ".keprix")) / "billing"
    root.mkdir(parents=True, exist_ok=True)
    return root / "workspace_feature_grandfather.json"


def _read() -> dict[str, dict[str, dict[str, Any]]]:
    try:
        value = json.loads(_path().read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write(value: dict[str, dict[str, dict[str, Any]]]) -> None:
    temporary = _path().with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(_path())


def workspace_has_feature_grandfather(workspace_id: str, feature: str) -> bool:
    return feature in _read().get(workspace_id, {})


def grant_feature_grandfather(workspace_id: str, feature: str, reason: str, created_at: str | None = None) -> bool:
    feature = feature.strip().lower()
    if feature not in _FEATURES:
        raise ValueError(f"unsupported feature: {feature}")
    data = _read()
    workspace = data.setdefault(workspace_id, {})
    if feature in workspace:
        return False
    workspace[feature] = {"workspace_id": workspace_id, "feature": feature, "reason": reason.strip(), "created_at": created_at or datetime.now(timezone.utc).isoformat()}
    _write(data)
    return True


def list_feature_grandfather(workspace_id: str) -> dict[str, dict[str, Any]]:
    return dict(_read().get(workspace_id, {}))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage Keprix feature grandfather exemptions")
    parser.add_argument("workspace_id")
    parser.add_argument("feature", nargs="?")
    parser.add_argument("--reason", default="")
    args = parser.parse_args()
    if args.feature:
        if not args.reason.strip():
            parser.error("--reason is required when granting an exemption")
        print(json.dumps({"created": grant_feature_grandfather(args.workspace_id, args.feature, args.reason)}))
    else:
        print(json.dumps(list_feature_grandfather(args.workspace_id), indent=2))
