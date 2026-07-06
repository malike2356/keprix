"""Pack install snapshots for rollback."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.hub.registry import hub_home


def snapshot_dir(name: str, version: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    path = hub_home() / "snapshots" / name / f"{version}-{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_snapshot(name: str, version: str, install_path: Path, manifest: dict[str, Any]) -> Path:
    target = snapshot_dir(name, version)
    if install_path.exists():
        shutil.copytree(install_path, target / "files", dirs_exist_ok=True)
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return target


def list_snapshots(name: str) -> list[Path]:
    root = hub_home() / "snapshots" / name
    if not root.exists():
        return []
    return sorted(root.iterdir(), reverse=True)


def restore_snapshot(name: str, version: str | None, install_path: Path) -> Path:
    snapshots = list_snapshots(name)
    if not snapshots:
        raise FileNotFoundError(f"No snapshots for {name}")
    chosen = snapshots[0]
    if version:
        matches = [path for path in snapshots if path.name.startswith(f"{version}-")]
        if not matches:
            raise FileNotFoundError(f"No snapshot for {name}@{version}")
        chosen = matches[0]
    files_dir = chosen / "files"
    if install_path.exists():
        shutil.rmtree(install_path)
    if files_dir.exists():
        shutil.copytree(files_dir, install_path)
    return chosen
