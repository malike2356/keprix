"""Haystack-style production RAG pipelines and routing."""

from keprix.rag_pipeline.evaluator import PipelineEvaluator, EvaluationReport
from keprix.rag_pipeline.pipeline import RagPipeline, PipelineRunResult, get_pipeline_registry
from keprix.rag_pipeline.router import PipelineRouter, RouteDecision

__all__ = [
    "EvaluationReport",
    "PipelineEvaluator",
    "PipelineRouter",
    "PipelineRunResult",
    "RagPipeline",
    "RouteDecision",
    "get_pipeline_registry",
]
