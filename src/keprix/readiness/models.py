"""Typed readiness check results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

CheckStatus = Literal["pass", "warn", "fail", "unknown"]
CheckCategory = Literal["market", "upgrade", "recovery"]


@dataclass
class CheckResult:
    id: str
    title: str
    category: CheckCategory
    status: CheckStatus
    summary: str
    fix_path: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    docs_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReadinessReport:
    generated_at: str
    overall: CheckStatus
    market: CheckStatus
    upgrade: CheckStatus
    recovery: CheckStatus
    checks: list[CheckResult]
    counts: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "overall": self.overall,
            "market": self.market,
            "upgrade": self.upgrade,
            "recovery": self.recovery,
            "counts": dict(self.counts),
            "notes": list(self.notes),
            "checks": [c.to_dict() for c in self.checks],
        }


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rollup(statuses: list[CheckStatus]) -> CheckStatus:
    if any(s == "fail" for s in statuses):
        return "fail"
    if any(s == "warn" for s in statuses):
        return "warn"
    if any(s == "unknown" for s in statuses) and not any(s == "pass" for s in statuses):
        return "unknown"
    if any(s == "unknown" for s in statuses):
        return "warn"
    return "pass"


def count_statuses(checks: list[CheckResult]) -> dict[str, int]:
    out = {"pass": 0, "warn": 0, "fail": 0, "unknown": 0}
    for check in checks:
        out[check.status] = out.get(check.status, 0) + 1
    return out
