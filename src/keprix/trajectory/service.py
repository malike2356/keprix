"""Fork, replay, and high-level trajectory operations."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from keprix.trajectory.store import TrajectoryStore, get_trajectory_store
from keprix.trajectory.types import TrajectoryEvent


class TrajectoryService:
    """Operator workflows on top of the append-only store."""

    def __init__(self, store: TrajectoryStore | None = None) -> None:
        self._store = store or get_trajectory_store()

    @property
    def store(self) -> TrajectoryStore:
        return self._store

    def create(
        self,
        *,
        workspace_id: str = "default",
        session_id: str | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._store.create_trajectory(
            workspace_id=workspace_id,
            session_id=session_id,
            title=title,
            metadata=metadata,
        )

    def append(
        self,
        trajectory_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> TrajectoryEvent:
        return self._store.append_event(
            trajectory_id, event_type, payload, **kwargs
        )

    def get(self, trajectory_id: str) -> dict[str, Any] | None:
        meta = self._store.get_trajectory(trajectory_id)
        if meta is None:
            return None
        events = self._store.list_events(trajectory_id)
        return {
            **meta,
            "events": [e.to_dict() for e in events],
            "event_count": len(events),
        }

    def search(self, **kwargs: Any) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._store.search_events(**kwargs)]

    def fork(
        self,
        trajectory_id: str,
        *,
        through_seq: int,
        title: str | None = None,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Clone events with ``seq <= through_seq`` into a new trajectory."""
        parent = self._store.get_trajectory(trajectory_id)
        if parent is None:
            raise KeyError(f"Unknown trajectory_id: {trajectory_id}")
        events = self._store.list_events(trajectory_id, limit=10000)
        prefix = [e for e in events if e.seq <= through_seq]
        if not prefix and through_seq > 0:
            raise ValueError(f"No events with seq <= {through_seq}")
        child = self._store.create_trajectory(
            workspace_id=workspace_id or parent["workspace_id"],
            session_id=None,
            parent_trajectory_id=trajectory_id,
            title=title or f"fork of {parent.get('title') or trajectory_id[:8]} @{through_seq}",
            metadata={
                "forked_from": trajectory_id,
                "through_seq": through_seq,
            },
        )
        for event in prefix:
            self._store.append_event(
                child["trajectory_id"],
                event.event_type,
                event.payload,
                tool_name=event.tool_name,
                soft_wall_outcome=event.soft_wall_outcome,
                error_text=event.error_text,
                timestamp=event.timestamp,
            )
        return {
            **child,
            "forked_event_count": len(prefix),
            "parent_trajectory_id": trajectory_id,
            "through_seq": through_seq,
        }

    def replay(
        self,
        trajectory_id: str,
        *,
        from_seq: int = 1,
        mode: str = "recorded",
        through_seq: int | None = None,
    ) -> dict[str, Any]:
        """Replay using recorded tool results by default (no live dangerous tools).

        ``mode=recorded`` (default): returns ordered steps with recorded
        tool_result payloads so callers can re-drive loops offline (prompt 772).

        ``mode=live``: marks soft_wall/shell/fs steps as requiring Soft Wall
        gating; does not execute commands here.
        """
        if mode not in {"recorded", "live"}:
            raise ValueError("mode must be 'recorded' or 'live'")
        events = self._store.list_events(trajectory_id, limit=10000)
        selected = [
            e
            for e in events
            if e.seq >= from_seq and (through_seq is None or e.seq <= through_seq)
        ]
        steps: list[dict[str, Any]] = []
        for event in selected:
            step: dict[str, Any] = {
                "seq": event.seq,
                "event_type": event.event_type,
                "tool_name": event.tool_name,
                "soft_wall_outcome": event.soft_wall_outcome,
                "payload": event.payload,
                "error_text": event.error_text,
                "timestamp": event.timestamp,
            }
            if mode == "recorded":
                step["execute"] = False
                step["use_recorded_result"] = event.event_type in {
                    "tool_result",
                    "soft_wall",
                    "mutation",
                    "message",
                    "error",
                    "checkpoint",
                    "note",
                    "tool_call",
                }
            else:
                # Live mode never auto-runs shell/fs; Soft Wall must gate.
                dangerous = (event.tool_name or "").lower() in {
                    "terminal",
                    "execute_code",
                    "write_file",
                    "bash",
                    "shell",
                } or event.event_type == "tool_call" and (
                    "rm " in str(event.payload).lower()
                    or "sudo" in str(event.payload).lower()
                )
                step["execute"] = not dangerous
                step["requires_soft_wall"] = bool(dangerous)
                step["use_recorded_result"] = False
            steps.append(step)
        return {
            "trajectory_id": trajectory_id,
            "mode": mode,
            "from_seq": from_seq,
            "through_seq": through_seq,
            "step_count": len(steps),
            "steps": steps,
            "live_dangerous_tools_blocked": mode == "recorded" or True,
        }

    def record_soft_wall(
        self,
        trajectory_id: str,
        *,
        outcome: str,
        tool_name: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> TrajectoryEvent:
        return self.append(
            trajectory_id,
            "soft_wall",
            detail or {},
            tool_name=tool_name,
            soft_wall_outcome=outcome,
        )

    def record_mutation(
        self,
        trajectory_id: str,
        *,
        stage: str,
        detail: dict[str, Any] | None = None,
        error_text: str | None = None,
    ) -> TrajectoryEvent:
        payload = {"stage": stage, **(detail or {})}
        return self.append(
            trajectory_id,
            "mutation",
            payload,
            error_text=error_text,
        )


_SERVICE: TrajectoryService | None = None
_SERVICE_LOCK = threading.Lock()


def get_trajectory_service(store: TrajectoryStore | None = None) -> TrajectoryService:
    global _SERVICE
    if store is not None:
        return TrajectoryService(store=store)
    with _SERVICE_LOCK:
        if _SERVICE is None:
            _SERVICE = TrajectoryService()
        return _SERVICE


def reset_trajectory_service_for_tests(
    sqlite_path: Path | None = None,
) -> TrajectoryService:
    global _SERVICE
    from keprix.trajectory.store import reset_trajectory_store_for_tests

    store = reset_trajectory_store_for_tests(sqlite_path=sqlite_path)
    with _SERVICE_LOCK:
        _SERVICE = TrajectoryService(store=store)
        return _SERVICE
