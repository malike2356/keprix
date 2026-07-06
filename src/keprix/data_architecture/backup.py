"""Backup and restore workspace data planes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from keprix.data_architecture.data_plane import get_workspace_data_plane


def backup_workspace(workspace_id: str = "default") -> Path:
    plane = get_workspace_data_plane(workspace_id)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = plane.root / "backups" / f"data_plane-{stamp}.sqlite"
    return plane.backup(dest)


def restore_workspace(source: Path, workspace_id: str = "default") -> None:
    get_workspace_data_plane(workspace_id).restore(source)
