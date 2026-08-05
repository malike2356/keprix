"""Filesystem store for Visual Playbook Studio documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


class PlaybookStudioStore:
    """Store runtime YAML and canvas layout side by side under ``~/.keprix/playbooks``."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path.home() / ".keprix" / "playbooks"

    def list_playbooks(self) -> list[dict[str, Any]]:
        self.root.mkdir(parents=True, exist_ok=True)
        items: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("*.yaml")):
            parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            stat = path.stat()
            items.append(
                {
                    "id": str(parsed.get("id") or path.stem),
                    "name": str(parsed.get("name") or parsed.get("id") or path.stem),
                    "updated_at": stat.st_mtime,
                }
            )
        return items

    def load(self, playbook_id: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
        yaml_path = self._yaml_path(playbook_id)
        if not yaml_path.exists():
            raise FileNotFoundError(playbook_id)
        yaml_doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        layout_path = self._layout_path(playbook_id)
        layout = None
        if layout_path.exists():
            layout = json.loads(layout_path.read_text(encoding="utf-8"))
        return yaml_doc, layout

    def save(
        self,
        playbook_id: str,
        yaml_doc: dict[str, Any],
        layout: dict[str, Any] | None,
    ) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._yaml_path(playbook_id).write_text(
            yaml.safe_dump(yaml_doc, sort_keys=False),
            encoding="utf-8",
        )
        if layout is not None:
            self._layout_path(playbook_id).write_text(
                json.dumps(layout, indent=2, sort_keys=True),
                encoding="utf-8",
            )

    def delete(self, playbook_id: str) -> None:
        for path in (self._yaml_path(playbook_id), self._layout_path(playbook_id)):
            if path.exists():
                path.unlink()

    def _yaml_path(self, playbook_id: str) -> Path:
        return self.root / f"{self._safe_id(playbook_id)}.yaml"

    def _layout_path(self, playbook_id: str) -> Path:
        return self.root / f"{self._safe_id(playbook_id)}.layout.json"

    @staticmethod
    def _safe_id(playbook_id: str) -> str:
        safe = "".join(ch for ch in playbook_id if ch.isalnum() or ch in {"_", "-"})
        if not safe:
            raise ValueError("playbook_id is required")
        return safe
