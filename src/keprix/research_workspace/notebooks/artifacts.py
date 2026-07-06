"""Artifact capture for notebook runs."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def collect_artifacts(workdir: Path) -> dict[str, list[str]]:
    figures = sorted(str(path) for path in workdir.glob("*.png"))
    tables = sorted(str(path) for path in workdir.glob("*.csv"))
    logs = sorted(str(path) for path in workdir.glob("execution.log"))
    return {"figures": figures, "tables": tables, "logs": logs}


def persist_run_artifacts(
    *,
    workdir: Path,
    artifact_root: Path,
    run_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    dest = artifact_root / run_id
    dest.mkdir(parents=True, exist_ok=True)
    copied: dict[str, list[str]] = {"figures": [], "tables": [], "logs": [], "notebooks": [], "scripts": []}
    for pattern in ("*.png", "*.csv", "execution.log", "*.ipynb", "*.py", "*.R", "*.html"):
        for path in workdir.glob(pattern):
            target = dest / path.name
            shutil.copy2(path, target)
            bucket = _bucket_for(path.suffix.lower())
            copied[bucket].append(str(target))
    manifest_path = dest / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    copied["manifest"] = [str(manifest_path)]
    return copied


def _bucket_for(suffix: str) -> str:
    if suffix in {".py", ".r"}:
        return "scripts"
    if suffix == ".ipynb":
        return "notebooks"
    if suffix == ".html":
        return "notebooks"
    if suffix == ".png":
        return "figures"
    if suffix == ".csv":
        return "tables"
    if suffix == ".log":
        return "logs"
    return "logs"
