"""RAG pipeline evaluation metrics and persistence."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.rag_pipeline.component import PipelineContext


@dataclass
class EvaluationReport:
    eval_id: str
    pipeline_id: str
    retrieval_precision: float
    citation_faithfulness: float
    answer_completeness: float
    hallucination_risk: float
    latency_ms: float
    cost_units: float
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "eval_id": self.eval_id,
            "pipeline_id": self.pipeline_id,
            "retrieval_precision": self.retrieval_precision,
            "citation_faithfulness": self.citation_faithfulness,
            "answer_completeness": self.answer_completeness,
            "hallucination_risk": self.hallucination_risk,
            "latency_ms": self.latency_ms,
            "cost_units": self.cost_units,
            "created_at": self.created_at,
            "details": self.details,
        }


class EvaluationStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path.home() / ".keprix" / "rag_pipeline" / "evaluations"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, report: EvaluationReport) -> Path:
        path = self.base_dir / f"{report.eval_id}.json"
        path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        return path

    def list_reports(self, pipeline_id: str | None = None, limit: int = 50) -> list[EvaluationReport]:
        reports: list[EvaluationReport] = []
        for path in sorted(self.base_dir.glob("*.json"), reverse=True):
            data = json.loads(path.read_text(encoding="utf-8"))
            if pipeline_id and data.get("pipeline_id") != pipeline_id:
                continue
            reports.append(EvaluationReport(**data))
            if len(reports) >= limit:
                break
        return reports


class PipelineEvaluator:
    def __init__(self, store: EvaluationStore | None = None) -> None:
        self.store = store or EvaluationStore()

    def evaluate_run(self, ctx: PipelineContext, *, pipeline_id: str = "default") -> EvaluationReport:
        started = time.perf_counter()
        retrieval_precision = self._retrieval_precision(ctx)
        citation_faithfulness = self._citation_faithfulness(ctx)
        answer_completeness = self._answer_completeness(ctx)
        hallucination_risk = self._hallucination_risk(ctx)
        latency_ms = sum(ctx.latency_ms.values())
        report = EvaluationReport(
            eval_id=str(uuid.uuid4()),
            pipeline_id=pipeline_id,
            retrieval_precision=retrieval_precision,
            citation_faithfulness=citation_faithfulness,
            answer_completeness=answer_completeness,
            hallucination_risk=hallucination_risk,
            latency_ms=latency_ms,
            cost_units=ctx.cost_units,
            details={
                "route": ctx.route,
                "confidence": ctx.confidence,
                "citation_count": len(ctx.citations),
            },
        )
        self.store.save(report)
        _ = started
        return report

    def _retrieval_precision(self, ctx: PipelineContext) -> float:
        if not ctx.ranked:
            return 0.0
        query_terms = {term for term in ctx.query.lower().split() if len(term) > 2}
        if not query_terms:
            return float(ctx.confidence)
        hits = 0
        for row in ctx.ranked:
            content = str(row.get("content") or "").lower()
            if any(term in content for term in query_terms):
                hits += 1
        return hits / len(ctx.ranked)

    def _citation_faithfulness(self, ctx: PipelineContext) -> float:
        if not ctx.citations or not ctx.answer:
            return 0.0
        overlap = 0
        answer_lower = ctx.answer.lower()
        for cite in ctx.citations:
            snippet = str(cite.get("snippet") or "").lower()
            words = [word for word in snippet.split() if len(word) > 3]
            if words and any(word in answer_lower for word in words[:5]):
                overlap += 1
        return overlap / len(ctx.citations)

    def _answer_completeness(self, ctx: PipelineContext) -> float:
        if not ctx.answer:
            return 0.0
        if ctx.route in {"clarification", "deep_research", "blocked"}:
            return 0.4
        base = min(1.0, len(ctx.answer) / 120.0)
        if ctx.citations:
            base = min(1.0, base + 0.2)
        return base

    def _hallucination_risk(self, ctx: PipelineContext) -> float:
        if ctx.route == "blocked":
            return 0.0
        if not ctx.citations and ctx.answer and ctx.route == "direct_answer":
            return 0.9
        if ctx.confidence < 0.35:
            return 0.7
        return max(0.0, 1.0 - ctx.confidence)
