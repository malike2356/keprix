"""IsolationCheck enum and finding/report data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class IsolationCheck(str, Enum):
    # Data integrity checks (query the DB)
    ORPHANED_ROWS = "orphaned_rows"
    CROSS_NAMESPACE_REFS = "cross_namespace_refs"
    EXPIRED_GRANTS = "expired_grants"
    STALE_QUOTA_PERIODS = "stale_quota_periods"
    SESSION_PRODUCT_MISMATCH = "session_product_mismatch"

    # Route coverage checks (static analysis)
    UNPROTECTED_ROUTES = "unprotected_routes"
    MISSING_WORKSPACE_FILTER = "missing_ws_filter"

    # Live checks (controlled test requests)
    CROSS_PRODUCT_LEAK = "cross_product_leak"
    TOOL_ACL_BYPASS = "tool_acl_bypass"
    EGRESS_GATE_BYPASS = "egress_gate_bypass"

    # Grant hygiene
    OVERLY_BROAD_GRANTS = "overly_broad_grants"
    GRANT_WITHOUT_EXPIRY = "grant_without_expiry"


SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


@dataclass
class IsolationFinding:
    check: IsolationCheck
    severity: str               # "critical" | "high" | "medium" | "low"
    description: str
    fix_available: bool = False
    count: int = 0
    table: str | None = None
    sample_ids: list[str] = field(default_factory=list)
    fix_description: str | None = None
    routes: list[str] = field(default_factory=list)

    @property
    def severity_level(self) -> int:
        return SEVERITY_ORDER.get(self.severity, 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check": self.check.value,
            "severity": self.severity,
            "description": self.description,
            "fix_available": self.fix_available,
            "count": self.count,
            "table": self.table,
            "fix_description": self.fix_description,
        }


@dataclass
class IsolationReport:
    run_at: datetime
    checks_run: list[IsolationCheck]
    findings: list[IsolationFinding]
    summary: dict[str, Any] = field(default_factory=dict)
    passed: bool = field(init=False, default=True)
    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        self.passed = not any(
            f.severity in ("critical", "high") for f in self.findings
        )
        if not self.summary:
            self.summary = self._build_summary()

    def _build_summary(self) -> dict[str, Any]:
        by_sev: dict[str, int] = {}
        for f in self.findings:
            by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
        return {
            "total_findings": len(self.findings),
            "by_severity": by_sev,
            "checks_run": len(self.checks_run),
            "passed": self.passed,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_at": self.run_at.isoformat(),
            "passed": self.passed,
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
            "duration_seconds": self.duration_seconds,
        }
