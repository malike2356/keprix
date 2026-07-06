"""Workspace path allowlist for control center."""

from __future__ import annotations

import os
from pathlib import Path

from keprix.security.validation import InputValidator, ValidationError
from keprix.workspace.core.constants import WORKSPACE_ROOT

_validator = InputValidator()


def allowed_workspace_roots() -> list[Path]:
    roots: list[Path] = [Path(WORKSPACE_ROOT).resolve()]
    data_dir = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if data_dir:
        roots.append(Path(data_dir).resolve())
    return roots


def validate_workspace_root(path: str, field_name: str = "workspace_root") -> str:
    cleaned = _validator.validate_string(path, field_name)
    candidate = Path(cleaned).expanduser().resolve()
    for root in allowed_workspace_roots():
        try:
            candidate.relative_to(root)
            return str(candidate)
        except ValueError:
            continue
    raise ValidationError(f"{field_name} must be under an allowlisted workspace root")
