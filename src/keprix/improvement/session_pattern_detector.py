"""Detect repeated task patterns in real workspace sessions."""

from __future__ import annotations

from typing import Any

from keprix.improvement.pattern_clustering import RepeatedTask, cluster_repeated_tasks
from keprix.improvement.task_extractor import SessionTaskEvidence, first_user_task
from keprix.workspace.repository import workspace_repo


def detect_session_patterns(
    user: dict[str, Any],
    *,
    session_count: int = 50,
    min_occurrences: int = 3,
) -> list[RepeatedTask]:
    evidence: list[SessionTaskEvidence] = []
    for row in workspace_repo.list_sessions(user, limit=session_count, offset=0):
        session_id = str(row.get("id") or row.get("session_id") or "")
        if not session_id:
            continue
        try:
            session = workspace_repo.get_session(user, session_id)
        except Exception:
            continue
        extracted = first_user_task(session_id, session.get("messages") or [])
        if extracted:
            evidence.append(extracted)
    return cluster_repeated_tasks(evidence, min_occurrences=min_occurrences)


def record_completed_session_for_patterns(
    user: dict[str, Any],
    session_id: str,
    *,
    min_occurrences: int = 3,
) -> list[RepeatedTask]:
    """Single hook target for CLI/gateway session-complete events."""
    _ = session_id
    return detect_session_patterns(user, min_occurrences=min_occurrences)
