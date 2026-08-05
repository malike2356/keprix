"""Repository index preflight gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.coding.preflight_store import PreflightGateResult


def run_repo_index_gate(payload: dict[str, Any]) -> PreflightGateResult:
    if payload.get("repo_index_present") or payload.get("repo_map_present"):
        return PreflightGateResult("repo_index", "pass", "Repository index is already available.", {"present": True})
    repo_path = payload.get("repo_path")
    if repo_path and Path(str(repo_path)).is_dir():
        return PreflightGateResult("repo_index", "warn", "Load repo map before codegen to avoid rereading the tree.", {"repo_path": repo_path})
    return PreflightGateResult("repo_index", "warn", "No repository index was provided for this coding session.", {})
