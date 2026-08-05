"""Skill proposal store and import pipeline for Agent OS."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.improvement.pattern_clustering import RepeatedTask
from keprix_constants import get_keprix_home


def _proposal_dir() -> Path:
    path = get_keprix_home() / "agent-os" / "skill-proposals"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _pending_queue_path() -> Path:
    return get_keprix_home() / "agent-os" / "skill-proposals-pending.json"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:48] or "agent-os-skill"


@dataclass
class SkillProposal:
    proposal_id: str
    source: str
    slug: str
    name: str
    description: str
    evidence_sessions: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    occurrence_count: int = 1
    confidence: float = 0.7
    estimated_tokens_per_run: int = 0
    status: str = "pending"
    rationale: str = ""
    audit_id: str | None = None
    skill_path: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillProposal":
        return cls(
            proposal_id=str(data.get("proposal_id") or uuid.uuid4()),
            source=str(data.get("source") or "audit"),
            slug=slugify(str(data.get("slug") or data.get("name") or data.get("description") or "agent-os-skill")),
            name=str(data.get("name") or data.get("description") or "Agent OS skill")[:80],
            description=str(data.get("description") or data.get("name") or "Repeatable workflow skill"),
            evidence_sessions=list(data.get("evidence_sessions") or []),
            tools_used=list(data.get("tools_used") or data.get("tools_hint") or []),
            occurrence_count=int(data.get("occurrence_count") or max(1, len(data.get("evidence_sessions") or []))),
            confidence=float(data.get("confidence") or 0.7),
            estimated_tokens_per_run=int(data.get("estimated_tokens_per_run") or 0),
            status=str(data.get("status") or "pending"),
            rationale=str(data.get("rationale") or ""),
            audit_id=data.get("audit_id"),
            skill_path=data.get("skill_path"),
            created_at=str(data.get("created_at") or datetime.now(timezone.utc).isoformat()),
            updated_at=str(data.get("updated_at") or datetime.now(timezone.utc).isoformat()),
        )


class SkillProposalStore:
    def path_for(self, proposal_id: str) -> Path:
        return _proposal_dir() / f"{proposal_id}.json"

    def save(self, proposal: SkillProposal) -> SkillProposal:
        proposal.updated_at = datetime.now(timezone.utc).isoformat()
        self.path_for(proposal.proposal_id).write_text(json.dumps(proposal.to_dict(), indent=2), encoding="utf-8")
        return proposal

    def get(self, proposal_id: str) -> SkillProposal | None:
        path = self.path_for(proposal_id)
        if not path.is_file():
            return None
        return SkillProposal.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list(self, status: str | None = None) -> list[SkillProposal]:
        rows: list[SkillProposal] = []
        for path in sorted(_proposal_dir().glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            proposal = SkillProposal.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if status and proposal.status != status:
                continue
            rows.append(proposal)
        return rows

    def import_pending_queue(self) -> list[SkillProposal]:
        path = _pending_queue_path()
        if not path.is_file():
            return []
        rows = json.loads(path.read_text(encoding="utf-8"))
        imported: list[SkillProposal] = []
        for row in rows:
            proposal = SkillProposal.from_dict(row)
            imported.append(self.save(proposal))
        path.unlink(missing_ok=True)
        return imported

    def create_from_repeated_task(self, task: RepeatedTask) -> SkillProposal:
        proposal = SkillProposal(
            proposal_id=str(uuid.uuid4()),
            source="pattern_detector",
            slug=slugify(task.description),
            name=task.description[:80],
            description=task.description,
            evidence_sessions=task.sessions,
            tools_used=task.tools_used,
            occurrence_count=task.occurrence_count,
            confidence=task.confidence,
            estimated_tokens_per_run=task.estimated_tokens_per_run,
            rationale=f"Detected {task.occurrence_count} similar sessions.",
        )
        return self.save(proposal)

    def reject(self, proposal_id: str) -> SkillProposal | None:
        proposal = self.get(proposal_id)
        if proposal is None:
            return None
        proposal.status = "rejected"
        return self.save(proposal)
