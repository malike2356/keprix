"""Analyze completed agent runs for improvement signals."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _runs_dir() -> Path:
    path = Path.home() / ".keprix" / "workspace" / "improvement" / "runs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _proposals_dir() -> Path:
    path = Path.home() / ".keprix" / "workspace" / "improvement" / "proposals"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class RunRecord:
    run_id: str
    agent_id: str
    ok: bool
    steps: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    eval_score: float | None = None
    cost_usd: float = 0.0
    user_corrections: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "ok": self.ok,
            "steps": self.steps,
            "tool_calls": self.tool_calls,
            "eval_score": self.eval_score,
            "cost_usd": self.cost_usd,
            "user_corrections": self.user_corrections,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class ImprovementProposal:
    proposal_id: str
    run_id: str
    agent_id: str
    category: str
    title: str
    detail: str
    status: str = "pending_approval"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "category": self.category,
            "title": self.title,
            "detail": self.detail,
            "status": self.status,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class RunAnalyzer:
    def save_run(self, record: RunRecord) -> Path:
        path = _runs_dir() / f"{record.run_id}.json"
        path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
        return path

    def load_run(self, run_id: str) -> RunRecord | None:
        path = _runs_dir() / f"{run_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return RunRecord(**data)

    def analyze(self, record: RunRecord) -> list[ImprovementProposal]:
        proposals: list[ImprovementProposal] = []
        if not record.ok:
            proposals.append(self._proposal(record, "repeated_failure", "Run failed", "Investigate failing steps and add guardrails."))
        failed_tools = [call for call in record.tool_calls if not call.get("ok", True)]
        if failed_tools:
            proposals.append(
                self._proposal(
                    record,
                    "tool_failure",
                    "Tool failures detected",
                    f"Failed tools: {', '.join(call.get('name', 'unknown') for call in failed_tools)}",
                    metadata={"tools": failed_tools},
                )
            )
        slow_steps = [step for step in record.steps if float(step.get("duration_ms", 0)) > 5000]
        if slow_steps:
            proposals.append(
                self._proposal(
                    record,
                    "slow_step",
                    "Slow steps detected",
                    f"{len(slow_steps)} step(s) exceeded 5s.",
                    metadata={"steps": slow_steps},
                )
            )
        if record.cost_usd > 1.0:
            proposals.append(self._proposal(record, "high_cost", "High run cost", f"Run cost ${record.cost_usd:.2f} exceeds threshold."))
        if record.user_corrections:
            proposals.append(
                self._proposal(
                    record,
                    "user_correction",
                    "User corrections recorded",
                    "; ".join(record.user_corrections[:3]),
                )
            )
        if record.eval_score is not None and record.eval_score < 0.7:
            proposals.append(
                self._proposal(
                    record,
                    "low_eval",
                    "Low evaluation score",
                    f"Eval score {record.eval_score:.2f} is below target.",
                )
            )
        for proposal in proposals:
            self._save_proposal(proposal)
        return proposals

    def list_proposals(self, *, status: str | None = None) -> list[ImprovementProposal]:
        items: list[ImprovementProposal] = []
        for path in _proposals_dir().glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            if status and data.get("status") != status:
                continue
            items.append(ImprovementProposal(**data))
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def approve_proposal(self, proposal_id: str) -> ImprovementProposal | None:
        path = _proposals_dir() / f"{proposal_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = "approved"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return ImprovementProposal(**data)

    def reject_proposal(self, proposal_id: str) -> ImprovementProposal | None:
        path = _proposals_dir() / f"{proposal_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = "rejected"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return ImprovementProposal(**data)

    def apply_proposal(self, proposal_id: str) -> ImprovementProposal | None:
        """Mark an approved proposal as applied (Soft Wall apply step)."""
        path = _proposals_dir() / f"{proposal_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("status") not in {"approved", "pending_approval", "pending"}:
            return None
        data["status"] = "applied"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return ImprovementProposal(**data)

    def defer_proposal(self, proposal_id: str) -> ImprovementProposal | None:
        path = _proposals_dir() / f"{proposal_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = "deferred"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return ImprovementProposal(**data)

    def _proposal(self, record: RunRecord, category: str, title: str, detail: str, metadata: dict | None = None) -> ImprovementProposal:
        return ImprovementProposal(
            proposal_id=str(uuid.uuid4()),
            run_id=record.run_id,
            agent_id=record.agent_id,
            category=category,
            title=title,
            detail=detail,
            metadata=metadata or {},
        )

    def _save_proposal(self, proposal: ImprovementProposal) -> None:
        path = _proposals_dir() / f"{proposal.proposal_id}.json"
        path.write_text(json.dumps(proposal.to_dict(), indent=2), encoding="utf-8")
