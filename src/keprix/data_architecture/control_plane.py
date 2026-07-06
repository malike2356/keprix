"""SaaS control-plane metadata (Postgres when configured, local fallback)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from keprix.database import get_session_factory


def _control_plane_path() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "control_plane"
    except Exception:
        root = Path.home() / ".keprix" / "control_plane"
    root.mkdir(parents=True, exist_ok=True)
    return root / "registry.json"


class ControlPlane:
    def __init__(self) -> None:
        self._path = _control_plane_path()
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if self._path.exists():
            return json.loads(self._path.read_text(encoding="utf-8"))
        tenant_id = os.environ.get("KEPRIX_TENANT_ID", "local")
        workspace_id = os.environ.get("KEPRIX_WORKSPACE_ID", "default")
        return {
            "tenant_id": tenant_id,
            "workspaces": [
                {
                    "workspace_id": workspace_id,
                    "name": "Default workspace",
                    "data_plane_path": str(Path.home() / ".keprix" / "workspaces" / workspace_id),
                }
            ],
        }

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def status(self) -> dict[str, Any]:
        factory = get_session_factory()
        return {
            "engine": "postgres" if factory is not None else "file",
            "tenant_id": self._data.get("tenant_id"),
            "workspaces": list(self._data.get("workspaces") or []),
        }

    def resolve_workspace(self, workspace_id: str) -> dict[str, Any] | None:
        for row in self._data.get("workspaces") or []:
            if row.get("workspace_id") == workspace_id:
                return row
        return None

    def link_data_plane(self, workspace_id: str, data_plane_path: str) -> dict[str, Any]:
        workspaces = list(self._data.get("workspaces") or [])
        found = False
        for row in workspaces:
            if row.get("workspace_id") == workspace_id:
                row["data_plane_path"] = data_plane_path
                found = True
                break
        if not found:
            workspaces.append({"workspace_id": workspace_id, "data_plane_path": data_plane_path})
        self._data["workspaces"] = workspaces
        self._save()
        return {"workspace_id": workspace_id, "data_plane_path": data_plane_path}


_control_plane: ControlPlane | None = None


def get_control_plane() -> ControlPlane:
    global _control_plane
    if _control_plane is None:
        _control_plane = ControlPlane()
    return _control_plane
