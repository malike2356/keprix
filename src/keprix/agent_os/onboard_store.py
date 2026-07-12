"""Persistent store for Agent OS onboard interview sessions."""

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


def onboard_root() -> Path:
    root = get_keprix_home() / "agent-os" / "onboard"
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass
class OnboardSession:
    workspace_id: str
    session_id: str = field(default_factory=lambda: f"onb-{uuid4().hex[:10]}")
    current_question: int = 1
    answers: dict[str, str] = field(default_factory=dict)
    status: str = "in_progress"
    output_paths: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OnboardSession":
        return cls(
            session_id=str(data["session_id"]),
            workspace_id=str(data.get("workspace_id") or "personal-os"),
            current_question=int(data.get("current_question") or 1),
            answers={str(k): str(v) for k, v in (data.get("answers") or {}).items()},
            status=str(data.get("status") or "in_progress"),
            output_paths={str(k): str(v) for k, v in (data.get("output_paths") or {}).items()},
            created_at=str(data.get("created_at") or _now()),
            completed_at=data.get("completed_at"),
        )


class OnboardStore:
    def path_for(self, session_id: str) -> Path:
        return onboard_root() / f"{session_id}.json"

    def create(self, workspace_id: str) -> OnboardSession:
        return self.save(OnboardSession(workspace_id=workspace_id))

    def save(self, session: OnboardSession) -> OnboardSession:
        self.path_for(session.session_id).write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
        return session

    def get(self, session_id: str) -> OnboardSession | None:
        path = self.path_for(session_id)
        if not path.is_file():
            return None
        return OnboardSession.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def latest_for_workspace(self, workspace_id: str) -> OnboardSession | None:
        sessions = [
            OnboardSession.from_dict(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(onboard_root().glob("onb-*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        ]
        return next((session for session in sessions if session.workspace_id == workspace_id), None)
