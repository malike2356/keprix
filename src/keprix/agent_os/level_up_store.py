"""Persistent Level-up remediation plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix_constants import get_keprix_home


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def level_up_root() -> Path:
    root = get_keprix_home() / "agent-os" / "level-up"
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass
class LevelUpAction:
    id: str
    title: str
    dimension: str
    leverage: str
    kind: str
    instructions_md: str
    action_url: str | None = None
    skill_slug: str | None = None
    completed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LevelUpAction":
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            dimension=str(data["dimension"]),
            leverage=str(data.get("leverage") or "medium"),
            kind=str(data.get("kind") or "manual"),
            action_url=data.get("action_url"),
            skill_slug=data.get("skill_slug"),
            instructions_md=str(data.get("instructions_md") or ""),
            completed=bool(data.get("completed", False)),
        )


@dataclass
class LevelUpPlan:
    source_audit_id: str
    actions: list[LevelUpAction]
    estimated_score_delta: float
    workspace_id: str | None = None
    workspace_path: str | None = None
    plan_id: str = field(default_factory=lambda: f"lvl-{uuid4().hex[:10]}")
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "source_audit_id": self.source_audit_id,
            "workspace_id": self.workspace_id,
            "workspace_path": self.workspace_path,
            "actions": [action.to_dict() for action in self.actions],
            "estimated_score_delta": self.estimated_score_delta,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LevelUpPlan":
        return cls(
            plan_id=str(data["plan_id"]),
            source_audit_id=str(data["source_audit_id"]),
            workspace_id=data.get("workspace_id"),
            workspace_path=data.get("workspace_path"),
            actions=[LevelUpAction.from_dict(row) for row in data.get("actions") or []],
            estimated_score_delta=float(data.get("estimated_score_delta") or 0),
            created_at=str(data.get("created_at") or _now()),
        )


class LevelUpStore:
    def path_for(self, plan_id: str) -> Path:
        return level_up_root() / f"{plan_id}.json"

    def save(self, plan: LevelUpPlan) -> LevelUpPlan:
        self.path_for(plan.plan_id).write_text(json.dumps(plan.to_dict(), indent=2), encoding="utf-8")
        return plan

    def get(self, plan_id: str) -> LevelUpPlan | None:
        path = self.path_for(plan_id)
        if not path.is_file():
            return None
        return LevelUpPlan.from_dict(json.loads(path.read_text(encoding="utf-8")))
