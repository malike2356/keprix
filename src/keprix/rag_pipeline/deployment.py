"""Deployment confidence checks for RAG pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from keprix.rag_pipeline.evaluator import EvaluationReport


@dataclass
class DeploymentCheck:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass
class DeploymentReport:
    pipeline_id: str
    ready: bool
    checks: list[DeploymentCheck]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "ready": self.ready,
            "checks": [check.to_dict() for check in self.checks],
        }


def assess_deployment(
    *,
    pipeline_id: str,
    evaluations: list[EvaluationReport],
    min_precision: float = 0.5,
    max_hallucination_risk: float = 0.6,
    max_latency_ms: float = 5000.0,
) -> DeploymentReport:
    checks: list[DeploymentCheck] = []
    if not evaluations:
        checks.append(DeploymentCheck("evaluations_present", False, "No evaluation reports found"))
        return DeploymentReport(pipeline_id=pipeline_id, ready=False, checks=checks)

    latest = evaluations[0]
    checks.append(
        DeploymentCheck(
            "retrieval_precision",
            latest.retrieval_precision >= min_precision,
            f"precision={latest.retrieval_precision:.2f} threshold={min_precision}",
        )
    )
    checks.append(
        DeploymentCheck(
            "hallucination_risk",
            latest.hallucination_risk <= max_hallucination_risk,
            f"risk={latest.hallucination_risk:.2f} threshold={max_hallucination_risk}",
        )
    )
    checks.append(
        DeploymentCheck(
            "latency",
            latest.latency_ms <= max_latency_ms,
            f"latency_ms={latest.latency_ms:.1f} threshold={max_latency_ms}",
        )
    )
    ready = all(check.passed for check in checks)
    return DeploymentReport(pipeline_id=pipeline_id, ready=ready, checks=checks)
