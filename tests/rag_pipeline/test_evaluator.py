"""Evaluator tests for RAG pipelines."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.rag_pipeline.component import PipelineContext
from keprix.rag_pipeline.deployment import assess_deployment
from keprix.rag_pipeline.evaluator import EvaluationStore, PipelineEvaluator


def test_evaluator_scores_run_and_persists(tmp_path: Path) -> None:
    evaluator = PipelineEvaluator(store=EvaluationStore(base_dir=tmp_path))
    ctx = PipelineContext(
        user_id="user-1",
        query="Building 3 maintenance",
        answer="Building 3 maintenance covers HVAC checks.",
        confidence=0.8,
        route="direct_answer",
        ranked=[{"content": "Building 3 maintenance schedule", "score": 0.8, "source": "doc:1"}],
        citations=[{"snippet": "Building 3 maintenance schedule", "source": "doc:1", "score": 0.8}],
        latency_ms={"retriever": 12.0, "ranker": 4.0},
        cost_units=0.02,
    )
    report = evaluator.evaluate_run(ctx, pipeline_id="eval-pipeline")
    assert 0.0 <= report.retrieval_precision <= 1.0
    assert 0.0 <= report.citation_faithfulness <= 1.0
    assert report.latency_ms == 16.0
    saved = list(tmp_path.glob("*.json"))
    assert saved


def test_deployment_assessment_uses_latest_evaluation(tmp_path: Path) -> None:
    evaluator = PipelineEvaluator(store=EvaluationStore(base_dir=tmp_path))
    ctx = PipelineContext(
        user_id="user-1",
        query="policy",
        answer="Retention policy keeps audit logs for 90 days with citations.",
        confidence=0.9,
        route="direct_answer",
        ranked=[{"content": "Retention policy keeps audit logs", "score": 0.9, "source": "doc:policy"}],
        citations=[{"snippet": "Retention policy keeps audit logs", "source": "doc:policy", "score": 0.9}],
    )
    report = evaluator.evaluate_run(ctx, pipeline_id="deploy-pipeline")
    deployment = assess_deployment(pipeline_id="deploy-pipeline", evaluations=[report])
    assert deployment.pipeline_id == "deploy-pipeline"
    assert isinstance(deployment.ready, bool)
    assert deployment.checks
