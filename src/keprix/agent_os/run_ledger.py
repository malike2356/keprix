"""Run ledger models for Agent OS automation executions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunLedgerEntry:
    entry_id: str
    source_type: str
    source_id: str
    run_id: str
    workspace_id: str
    status: str
    input_summary: dict[str, Any] = field(default_factory=dict)
    output_summary: dict[str, Any] = field(default_factory=dict)
    eval_score: float | None = None
    tokens: int = 0
    duration_ms: int = 0
    user_corrections: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def create(
        cls,
        *,
        source_type: str,
        source_id: str,
        run_id: str,
        workspace_id: str,
        status: str,
        input_summary: dict[str, Any] | None = None,
        output_summary: dict[str, Any] | None = None,
        eval_score: float | None = None,
        tokens: int = 0,
        duration_ms: int = 0,
        user_corrections: list[str] | None = None,
    ) -> "RunLedgerEntry":
        return cls(
            entry_id=f"rle_{uuid4().hex}",
            source_type=source_type,
            source_id=source_id,
            run_id=run_id,
            workspace_id=workspace_id,
            status=status,
            input_summary=input_summary or {},
            output_summary=output_summary or {},
            eval_score=eval_score,
            tokens=max(0, int(tokens or 0)),
            duration_ms=max(0, int(duration_ms or 0)),
            user_corrections=list(user_corrections or []),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "run_id": self.run_id,
            "workspace_id": self.workspace_id,
            "status": self.status,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "eval_score": self.eval_score,
            "tokens": self.tokens,
            "duration_ms": self.duration_ms,
            "user_corrections": self.user_corrections,
            "created_at": self.created_at,
        }


@dataclass
class LoopProfile:
    source_type: str
    source_id: str
    baseline_entry_ids: list[str] = field(default_factory=list)
    improvement_proposals: list[dict[str, Any]] = field(default_factory=list)

    @property
    def profile_id(self) -> str:
        return f"{self.source_type}:{self.source_id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "baseline_entry_ids": self.baseline_entry_ids,
            "improvement_proposals": self.improvement_proposals,
        }
