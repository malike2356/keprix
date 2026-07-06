"""Append-only job audit events."""

from __future__ import annotations

import json
from typing import Any

from keprix.data_architecture.data_plane import WorkspaceDataPlane, get_workspace_data_plane


def append_job_event(
    job_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    *,
    plane: WorkspaceDataPlane | None = None,
) -> None:
    target = plane or get_workspace_data_plane()
    with target.connect(write=True) as conn:
        conn.execute(
            """
            INSERT INTO local_job_events (job_id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, datetime('now'))
            """,
            (job_id, event_type, json.dumps(payload or {})),
        )
