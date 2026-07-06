"""Cost metering for agent runs (Prompt 57)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CostEntry:
    run_id: str
    workspace_id: str
    cost_usd: float
    tags: dict[str, Any] = field(default_factory=dict)


class CostMeter:
    def __init__(self) -> None:
        self._entries: list[CostEntry] = []

    def record(self, run_id: str, cost_usd: float, *, workspace_id: str = "", tags: dict[str, Any] | None = None) -> None:
        self._entries.append(
            CostEntry(run_id=run_id, workspace_id=workspace_id, cost_usd=cost_usd, tags=tags or {})
        )

    def total(self, *, workspace_id: str | None = None) -> float:
        entries = self._entries
        if workspace_id:
            entries = [entry for entry in entries if entry.workspace_id == workspace_id]
        return sum(entry.cost_usd for entry in entries)

    def dashboard(self, *, limit: int = 20) -> dict[str, Any]:
        total = self.total()
        recent = [
            {"run_id": entry.run_id, "workspace_id": entry.workspace_id, "cost_usd": entry.cost_usd}
            for entry in self._entries[-limit:]
        ]
        return {"total_cost_usd": total, "run_count": len(self._entries), "recent": recent}

    def clear(self) -> None:
        self._entries.clear()


_cost_meter: CostMeter | None = None


def get_cost_meter() -> CostMeter:
    global _cost_meter
    if _cost_meter is None:
        _cost_meter = CostMeter()
    return _cost_meter


def record_cost(run_id: str, cost_usd: float, *, workspace_id: str = "") -> None:
    get_cost_meter().record(run_id, cost_usd, workspace_id=workspace_id)
