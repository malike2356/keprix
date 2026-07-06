"""Deployment bundle builder for agent apps."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from keprix.agent_apps.app_manifest import load_manifest, validate_manifest

EXCLUDED_PARTS = {
    ".env",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".cache",
    "node_modules",
    ".venv",
    "venv",
}


def _should_exclude(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDED_PARTS:
        return True
    if path.name.endswith((".pyc", ".log", ".sqlite", ".db")):
        return True
    if path.name.startswith(".env"):
        return True
    return False


def build_deployment_bundle(app_dir: Path, output_path: Path, *, target: str = "local") -> dict[str, str]:
    manifest = load_manifest(app_dir)
    validate_manifest(manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in app_dir.rglob("*"):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(app_dir)
            if any(part in EXCLUDED_PARTS for part in rel.parts):
                continue
            if _should_exclude(rel):
                continue
            archive.write(file_path, arcname=str(rel))
        metadata = {
            "name": manifest.name,
            "version": manifest.version,
            "target": target,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "excluded": sorted(EXCLUDED_PARTS),
        }
        archive.writestr("bundle.json", json.dumps(metadata, indent=2))
    return {"bundle_path": str(output_path), "target": target, "app": manifest.name}
