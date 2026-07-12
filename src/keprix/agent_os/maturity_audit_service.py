"""Four C's maturity audit service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.agent_os.maturity_audit_store import MaturityAuditResult, MaturityAuditStore
from keprix.agent_os.maturity_scorers import score_cadence, score_capabilities, score_connections, score_context
from keprix.workspace.template_presets import workspace_root


class MaturityAuditService:
    def __init__(self, store: MaturityAuditStore | None = None) -> None:
        self.store = store or MaturityAuditStore()

    def run(self, *, workspace_id: str | None = None, workspace_path: str | None = None) -> MaturityAuditResult:
        root = Path(workspace_path).expanduser().resolve() if workspace_path else workspace_root(workspace_id or "personal-os")
        connections_score, missing = score_connections(root)
        scores = [
            score_context(root),
            connections_score,
            score_capabilities(root),
            score_cadence(root),
        ]
        result = MaturityAuditResult(
            workspace_id=workspace_id,
            scores=scores,
            top_gaps=self._rank_gaps(scores),
            tier1_domains_missing=missing,
        )
        return self.store.save(result)

    def get(self, audit_id: str) -> MaturityAuditResult | None:
        return self.store.get(audit_id)

    def list(self, limit: int = 50) -> list[MaturityAuditResult]:
        return self.store.list(limit=limit)

    def export_to_level_up(self, audit_id: str) -> dict[str, Any]:
        result = self.get(audit_id)
        if result is None:
            raise KeyError(audit_id)
        return {
            "schema": "keprix.level_up.input.v1",
            "source": "four-cs-maturity-audit",
            "audit_id": result.audit_id,
            "workspace_id": result.workspace_id,
            "total_score": result.total_score,
            "scores": [score.to_dict() for score in result.scores],
            "top_gaps": result.top_gaps,
            "tier1_domains_missing": result.tier1_domains_missing,
        }

    def _rank_gaps(self, scores) -> list[dict[str, Any]]:
        leverage = {"context": 90, "connections": 80, "capabilities": 70, "cadence": 60}
        rows: list[dict[str, Any]] = []
        for score in scores:
            for gap in score.gaps:
                rows.append(
                    {
                        "leverage": leverage.get(score.dimension, 50),
                        "title": gap,
                        "dimension": score.dimension,
                        "fix_hint": self._fix_hint(score.dimension),
                        "prompt_ref": {"context": 276, "connections": 277, "capabilities": 260, "cadence": 261}.get(score.dimension),
                    }
                )
        rows.sort(key=lambda row: row["leverage"], reverse=True)
        for index, row in enumerate(rows, start=1):
            row["rank"] = index
        return rows[:8]

    def _fix_hint(self, dimension: str) -> str:
        return {
            "context": "Run /onboard or fill context/*.md.",
            "connections": "Open the connections matrix and mark one tier-1 domain live.",
            "capabilities": "Approve skills and promote one to automation.",
            "cadence": "Schedule a weekly audit or run ledger cadence.",
        }.get(dimension, "Review this maturity gap.")
