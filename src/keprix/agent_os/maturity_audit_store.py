"""Persistent store for Four C's maturity audits."""

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


def maturity_root() -> Path:
    root = get_keprix_home() / "agent-os" / "maturity"
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass
class MaturityScore:
    dimension: str
    score: float
    strengths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    max_score: float = 25.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MaturityScore":
        return cls(
            dimension=str(data["dimension"]),
            score=float(data.get("score") or 0),
            max_score=float(data.get("max_score") or 25),
            strengths=list(data.get("strengths") or []),
            gaps=list(data.get("gaps") or []),
        )


@dataclass
class MaturityAuditResult:
    workspace_id: str | None
    scores: list[MaturityScore]
    top_gaps: list[dict[str, Any]]
    tier1_domains_missing: list[str]
    audit_id: str = field(default_factory=lambda: f"mat-{uuid4().hex[:10]}")
    scanned_at: str = field(default_factory=_now)

    @property
    def total_score(self) -> float:
        return round(sum(score.score for score in self.scores), 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "workspace_id": self.workspace_id,
            "total_score": self.total_score,
            "scores": [score.to_dict() for score in self.scores],
            "top_gaps": self.top_gaps,
            "tier1_domains_missing": self.tier1_domains_missing,
            "scanned_at": self.scanned_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MaturityAuditResult":
        return cls(
            audit_id=str(data["audit_id"]),
            workspace_id=data.get("workspace_id"),
            scores=[MaturityScore.from_dict(row) for row in data.get("scores") or []],
            top_gaps=list(data.get("top_gaps") or []),
            tier1_domains_missing=list(data.get("tier1_domains_missing") or []),
            scanned_at=str(data.get("scanned_at") or _now()),
        )


class MaturityAuditStore:
    def path_for(self, audit_id: str) -> Path:
        return maturity_root() / f"{audit_id}.json"

    def save(self, result: MaturityAuditResult) -> MaturityAuditResult:
        self.path_for(result.audit_id).write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        return result

    def get(self, audit_id: str) -> MaturityAuditResult | None:
        path = self.path_for(audit_id)
        if not path.is_file():
            return None
        return MaturityAuditResult.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list(self, limit: int = 50) -> list[MaturityAuditResult]:
        paths = sorted(maturity_root().glob("mat-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        return [MaturityAuditResult.from_dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths[:limit]]
