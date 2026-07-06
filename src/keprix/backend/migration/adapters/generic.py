"""Generic JSON manifest adapter (Prompt 42)."""

from __future__ import annotations

import json
from pathlib import Path

from keprix.backend.migration.manifest import AgentMigrationManifest


class GenericAdapter:
    def convert(self, source_path: Path) -> AgentMigrationManifest:
        if source_path.is_dir():
            manifest_path = source_path / "manifest.json"
            if not manifest_path.exists():
                raise ValueError("generic adapter requires manifest.json in directory")
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            payload = json.loads(source_path.read_text(encoding="utf-8"))
        return AgentMigrationManifest.model_validate(payload)
