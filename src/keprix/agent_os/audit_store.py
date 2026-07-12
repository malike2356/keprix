"""Persist workflow audit documents under KEPRIX_HOME."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix_constants import get_keprix_home


def _audits_dir() -> Path:
    path = get_keprix_home() / "agent-os" / "audits"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _proposals_queue_path() -> Path:
    path = get_keprix_home() / "agent-os" / "skill-proposals-pending.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class AuditTask:
    id: str
    domain: str
    description: str
    frequency: str = "weekly"
    desired_output: str = ""
    tools_hint: list[str] = field(default_factory=list)
    propose_skill: bool = True
    propose_automation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowAuditResult:
    audit_id: str
    mode: str
    status: str
    tasks: list[AuditTask] = field(default_factory=list)
    proposed_skills: list[dict[str, Any]] = field(default_factory=list)
    proposed_automations: list[dict[str, Any]] = field(default_factory=list)
    session_ids_scanned: list[str] = field(default_factory=list)
    interview_transcript: list[dict[str, str]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    user_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tasks"] = [task.to_dict() for task in self.tasks]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowAuditResult:
        tasks = [AuditTask(**item) for item in data.get("tasks") or []]
        return cls(
            audit_id=data["audit_id"],
            mode=data["mode"],
            status=data.get("status", "in_progress"),
            tasks=tasks,
            proposed_skills=list(data.get("proposed_skills") or []),
            proposed_automations=list(data.get("proposed_automations") or []),
            session_ids_scanned=list(data.get("session_ids_scanned") or []),
            interview_transcript=list(data.get("interview_transcript") or []),
            created_at=data.get("created_at") or datetime.now(timezone.utc).isoformat(),
            completed_at=data.get("completed_at"),
            user_id=data.get("user_id"),
        )


class AuditStore:
    def create(self, mode: str, user_id: str | None = None) -> WorkflowAuditResult:
        audit = WorkflowAuditResult(
            audit_id=str(uuid.uuid4()),
            mode=mode,
            status="in_progress",
            user_id=user_id,
        )
        self.save(audit)
        return audit

    def path_for(self, audit_id: str) -> Path:
        return _audits_dir() / f"{audit_id}.json"

    def save(self, audit: WorkflowAuditResult) -> None:
        self.path_for(audit.audit_id).write_text(
            json.dumps(audit.to_dict(), indent=2),
            encoding="utf-8",
        )

    def load(self, audit_id: str) -> WorkflowAuditResult | None:
        path = self.path_for(audit_id)
        if not path.is_file():
            return None
        return WorkflowAuditResult.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_audits(self, user_id: str | None = None) -> list[WorkflowAuditResult]:
        rows: list[WorkflowAuditResult] = []
        for path in sorted(_audits_dir().glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            audit = WorkflowAuditResult.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if user_id and audit.user_id and audit.user_id != user_id:
                continue
            rows.append(audit)
        return rows

    def append_proposals_queue(self, proposals: list[dict[str, Any]]) -> int:
        path = _proposals_queue_path()
        existing: list[dict[str, Any]] = []
        if path.is_file():
            existing = json.loads(path.read_text(encoding="utf-8"))
        existing.extend(proposals)
        path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        return len(proposals)
