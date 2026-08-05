"""Community vs Enterprise edition model."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from fastapi import HTTPException

Edition = Literal["community", "enterprise"]

FEATURE_MATRIX: dict[str, dict[Edition, bool]] = {
    "visual_studio": {"community": True, "enterprise": True},
    "yaml_playbooks": {"community": True, "enterprise": True},
    "local_agent": {"community": True, "enterprise": True},
    "basic_mcp": {"community": True, "enterprise": True},
    "fleet_deploy": {"community": False, "enterprise": True},
    "sso": {"community": False, "enterprise": True},
    "audit_export": {"community": False, "enterprise": True},
    "scout_fleet_dashboard": {"community": False, "enterprise": True},
    "connector_governance": {"community": False, "enterprise": True},
    "org_playbook_publish": {"community": False, "enterprise": True},
    "shared_template_library": {"community": False, "enterprise": True},
}


def current_edition() -> Edition:
    env_value = os.environ.get("KEPRIX_EDITION")
    if env_value in {"community", "enterprise"}:
        return env_value  # type: ignore[return-value]
    license_path = Path.home() / ".keprix" / "license.json"
    if license_path.exists():
        try:
            value = json.loads(license_path.read_text(encoding="utf-8")).get("edition")
            if value in {"community", "enterprise"}:
                return value
        except Exception:
            pass
    return "community"


def feature_enabled(feature: str) -> bool:
    return bool(FEATURE_MATRIX.get(feature, {}).get(current_edition(), False))


def require_enterprise(feature: str) -> None:
    if feature_enabled(feature):
        return
    raise HTTPException(
        status_code=403,
        detail={
            "error": "enterprise_required",
            "code": "enterprise_required",
            "feature": feature,
        },
    )
