"""Persistent store for coding preflight reports."""

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


def _safe_session_id(session_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in str(session_id or "default"))
    return cleaned or "default"


def preflight_dir() -> Path:
    path = get_keprix_home() / "agent-os" / "preflight"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class PreflightGateResult:
    gate: str
    status: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PreflightReport:
    session_id: str
    results: list[PreflightGateResult]
    overall: str
    tokens_saved_estimate: int
    report_id: str = field(default_factory=lambda: uuid4().hex[:12])
    created_at: str = field(default_factory=_now)
    override_applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "session_id": self.session_id,
            "results": [result.to_dict() for result in self.results],
            "overall": self.overall,
            "tokens_saved_estimate": self.tokens_saved_estimate,
            "created_at": self.created_at,
            "override_applied": self.override_applied,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PreflightReport":
        return cls(
            report_id=str(data["report_id"]),
            session_id=str(data["session_id"]),
            results=[PreflightGateResult(**item) for item in data.get("results", [])],
            overall=str(data.get("overall") or "proceed"),
            tokens_saved_estimate=int(data.get("tokens_saved_estimate") or 0),
            created_at=str(data.get("created_at") or _now()),
            override_applied=bool(data.get("override_applied", False)),
        )


class PreflightStore:
    def path(self, session_id: str) -> Path:
        return preflight_dir() / f"{_safe_session_id(session_id)}.json"

    def save(self, report: PreflightReport) -> PreflightReport:
        self.path(report.session_id).write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        return report

    def get(self, session_id: str) -> PreflightReport | None:
        path = self.path(session_id)
        if not path.is_file():
            return None
        return PreflightReport.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def override(self, session_id: str) -> PreflightReport | None:
        report = self.get(session_id)
        if report is None:
            return None
        report.override_applied = True
        if report.overall == "block":
            report.overall = "warn"
        for result in report.results:
            if result.status == "block":
                result.metadata["overridden"] = True
        return self.save(report)
