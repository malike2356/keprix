"""DiscoveryState: aggregated workspace signals for the home page discovery card system.

Provides the data the frontend needs to evaluate which discovery trigger to show.
Designed to be fast (<100ms): counts only, no full objects.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DiscoveryState:
    quota_usage_pct: Optional[int] = None
    brain_health_score: Optional[int] = None
    memory_count: int = 0
    brain_graph_visited: bool = False
    session_count: int = 0
    skill_count: int = 0
    completed_task_count: int = 0
    playbook_count: int = 0
    voice_provisioned: bool = False
    workspace_age_days: int = 0

    def to_dict(self) -> dict:
        return {
            "quotaUsagePct": self.quota_usage_pct,
            "brainHealthScore": self.brain_health_score,
            "memoryCount": self.memory_count,
            "brainGraphVisited": self.brain_graph_visited,
            "sessionCount": self.session_count,
            "skillCount": self.skill_count,
            "completedTaskCount": self.completed_task_count,
            "playbookCount": self.playbook_count,
            "voiceProvisioned": self.voice_provisioned,
            "workspaceAgeDays": self.workspace_age_days,
        }


@dataclass
class ActedOnRecord:
    trigger_id: str
    acted_at: float


class DiscoveryStateStore:
    """In-memory store for per-workspace discovery state with asyncio lock.

    In production this would be backed by a database table, but for the
    initial build an in-memory store per workspace is sufficient.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._brain_graph_visited: dict[str, bool] = {}
        self._acted_on: dict[str, list[ActedOnRecord]] = {}

    async def mark_brain_graph_visited(self, workspace_id: str) -> None:
        async with self._lock:
            self._brain_graph_visited[workspace_id] = True

    async def is_brain_graph_visited(self, workspace_id: str) -> bool:
        async with self._lock:
            return self._brain_graph_visited.get(workspace_id, False)

    async def mark_acted_on(self, workspace_id: str, trigger_id: str, acted_at: float) -> None:
        async with self._lock:
            records = self._acted_on.setdefault(workspace_id, [])
            records.append(ActedOnRecord(trigger_id=trigger_id, acted_at=acted_at))

    async def get_acted_on_ids(self, workspace_id: str) -> set[str]:
        async with self._lock:
            records = self._acted_on.get(workspace_id, [])
            return {r.trigger_id for r in records}


_store: DiscoveryStateStore | None = None


def get_discovery_store() -> DiscoveryStateStore:
    global _store
    if _store is None:
        _store = DiscoveryStateStore()
    return _store


def reset_discovery_store() -> None:
    global _store
    _store = None
