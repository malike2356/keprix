"""Convert improvement proposals into eval cases."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.improvement.run_analyzer import ImprovementProposal, RunRecord


def _eval_dir() -> Path:
    path = Path.home() / ".keprix" / "workspace" / "improvement" / "eval_cases"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class EvalCase:
    eval_id: str
    proposal_id: str
    agent_id: str
    title: str
    input: dict[str, Any]
    expected: dict[str, Any]
    source_run_id: str
    status: str = "draft"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "eval_id": self.eval_id,
            "proposal_id": self.proposal_id,
            "agent_id": self.agent_id,
            "title": self.title,
            "input": self.input,
            "expected": self.expected,
            "source_run_id": self.source_run_id,
            "status": self.status,
            "created_at": self.created_at,
        }


def proposal_to_eval_case(record: RunRecord, proposal: ImprovementProposal) -> EvalCase:
    return EvalCase(
        eval_id=str(uuid.uuid4()),
        proposal_id=proposal.proposal_id,
        agent_id=record.agent_id,
        title=f"Regression: {proposal.title}",
        input={
            "task": record.metadata.get("task") or record.metadata.get("message") or proposal.title,
            "context": record.metadata,
        },
        expected={
            "ok": True,
            "category": proposal.category,
            "must_not_repeat": proposal.detail,
        },
        source_run_id=record.run_id,
    )


def save_eval_case(case: EvalCase) -> Path:
    path = _eval_dir() / f"{case.eval_id}.json"
    path.write_text(json.dumps(case.to_dict(), indent=2), encoding="utf-8")
    return path


def list_eval_cases(*, proposal_id: str | None = None) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for path in _eval_dir().glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if proposal_id and data.get("proposal_id") != proposal_id:
            continue
        cases.append(EvalCase(**data))
    return cases
