"""Persistent opportunity registry."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.opportunity.models import OpportunityRequest
from keprix.opportunity.workspace import (
    create_opportunity_workspace,
    load_opportunity_workspace,
    opportunities_root,
    update_opportunity_json,
)
from keprix.opportunity.models import OpportunityWorkspace


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class OpportunityRecord:
    opportunity_id: str
    workspace_id: str
    user_id: str
    title: str
    slug: str
    status: str = "draft"
    niche: str | None = None
    market: str | None = None
    goal: str | None = None
    created_at: str = field(default_factory=lambda: _utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: _utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OpportunityRegistry:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or opportunities_root()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "index.json"
        self._events_path = self._dir / "events.jsonl"
        self._records: dict[str, OpportunityRecord] = {}
        self._event_seq = 0
        self._load()

    def _load(self) -> None:
        if self._index_path.exists():
            rows = json.loads(self._index_path.read_text(encoding="utf-8"))
            for row in rows:
                record = OpportunityRecord(**row)
                self._records[record.opportunity_id] = record
        if self._events_path.exists():
            for line in self._events_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = json.loads(line)
                self._event_seq = max(self._event_seq, int(event.get("id", 0)))

    def _save_index(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        rows = [record.to_dict() for record in self._records.values()]
        self._index_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def append_event(self, opportunity_id: str, event_type: str, payload: dict[str, Any]) -> int:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._event_seq += 1
        row = {
            "id": self._event_seq,
            "opportunity_id": opportunity_id,
            "event_type": event_type,
            "payload": payload,
            "emitted_at": _utcnow().isoformat(),
        }
        with self._events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
        return self._event_seq

    def create(self, *, user_id: str, request: OpportunityRequest) -> OpportunityWorkspace:
        workspace = create_opportunity_workspace(request)
        record = OpportunityRecord(
            opportunity_id=workspace.opportunity_id,
            workspace_id=workspace.workspace_id,
            user_id=user_id,
            title=workspace.title,
            slug=workspace.slug,
            status=workspace.status,
            niche=workspace.niche,
            market=workspace.market,
            goal=workspace.goal,
        )
        self._records[workspace.opportunity_id] = record
        self._save_index()
        self.append_event(workspace.opportunity_id, "opportunity.created", {"title": workspace.title})
        return workspace

    def get(self, opportunity_id: str) -> OpportunityRecord | None:
        return self._records.get(opportunity_id)

    def list_for_user(self, user_id: str) -> list[OpportunityRecord]:
        return [record for record in self._records.values() if record.user_id == user_id]

    def list_all(self) -> list[OpportunityRecord]:
        return list(self._records.values())

    def update_status(self, opportunity_id: str, status: str) -> OpportunityRecord:
        record = self._records.get(opportunity_id)
        if record is None:
            raise KeyError(opportunity_id)
        record.status = status
        record.updated_at = _utcnow().isoformat()
        update_opportunity_json(opportunity_id, {"status": status})
        self._save_index()
        return record

    def load_workspace(self, opportunity_id: str) -> OpportunityWorkspace:
        if opportunity_id not in self._records:
            raise KeyError(opportunity_id)
        return load_opportunity_workspace(opportunity_id)


_registry: OpportunityRegistry | None = None


def get_opportunity_registry() -> OpportunityRegistry:
    global _registry
    if _registry is None:
        _registry = OpportunityRegistry()
    return _registry


def reset_opportunity_registry(base_dir: Path | None = None) -> OpportunityRegistry:
    global _registry
    _registry = OpportunityRegistry(base_dir=base_dir)
    return _registry
