"""Explicit Haystack-style pipeline components."""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from keprix.memory.embeddings import EmbeddingService
from keprix.memory.rag.indexer import chunk_text, parse_markdown, parse_plaintext


@dataclass
class PipelineContext:
    user_id: str
    query: str = ""
    source_type: str = "plaintext"
    source_id: str = ""
    raw_content: str = ""
    cleaned_content: str = ""
    chunks: list[str] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)
    retrieved: list[dict[str, Any]] = field(default_factory=list)
    ranked: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    answer: str = ""
    route: str = "direct_answer"
    confidence: float = 0.0
    trace: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    latency_ms: dict[str, float] = field(default_factory=dict)
    cost_units: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "query": self.query,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "chunks": self.chunks,
            "retrieved": self.retrieved,
            "ranked": self.ranked,
            "citations": self.citations,
            "answer": self.answer,
            "route": self.route,
            "confidence": self.confidence,
            "trace": self.trace,
            "metadata": self.metadata,
            "latency_ms": self.latency_ms,
            "cost_units": self.cost_units,
        }


class PipelineComponent(ABC):
    name: str = "component"

    @abstractmethod
    async def run(self, ctx: PipelineContext) -> PipelineContext:
        raise NotImplementedError


class ConverterComponent(PipelineComponent):
    name = "converter"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        started = time.perf_counter()
        source_type = ctx.source_type.lower()
        if source_type == "markdown":
            ctx.cleaned_content = parse_markdown(ctx.raw_content)
        else:
            ctx.cleaned_content = parse_plaintext(ctx.raw_content)
        ctx.latency_ms[self.name] = (time.perf_counter() - started) * 1000
        ctx.trace.append({"component": self.name, "output_chars": len(ctx.cleaned_content)})
        return ctx


class CleanerComponent(PipelineComponent):
    name = "cleaner"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        started = time.perf_counter()
        text = ctx.cleaned_content or ctx.raw_content
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"[^\w\s.,;:!?\-'\"()/]", " ", text)
        ctx.cleaned_content = " ".join(text.split())
        ctx.latency_ms[self.name] = (time.perf_counter() - started) * 1000
        ctx.trace.append({"component": self.name, "output_chars": len(ctx.cleaned_content)})
        return ctx


class SplitterComponent(PipelineComponent):
    name = "splitter"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        started = time.perf_counter()
        text = ctx.cleaned_content or ctx.raw_content
        ctx.chunks = chunk_text(text, chunk_tokens=512, overlap_tokens=64)
        ctx.latency_ms[self.name] = (time.perf_counter() - started) * 1000
        ctx.trace.append({"component": self.name, "chunk_count": len(ctx.chunks)})
        return ctx


class EmbedderComponent(PipelineComponent):
    name = "embedder"

    def __init__(self, embeddings: EmbeddingService | None = None) -> None:
        self.embeddings = embeddings or EmbeddingService(deterministic=True)

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        started = time.perf_counter()
        ctx.embeddings = []
        for chunk in ctx.chunks:
            ctx.embeddings.append(await self.embeddings.embed(chunk))
            ctx.cost_units += 0.001
        ctx.latency_ms[self.name] = (time.perf_counter() - started) * 1000
        ctx.trace.append({"component": self.name, "embedded": len(ctx.embeddings)})
        return ctx


class RetrieverComponent(PipelineComponent):
    name = "retriever"

    def __init__(self, retriever: Any) -> None:
        self.retriever = retriever

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        started = time.perf_counter()
        source_types = ctx.metadata.get("source_types")
        if ctx.metadata.get("hybrid", True):
            ctx.retrieved = await self.retriever.hybrid_search(
                ctx.user_id,
                ctx.query,
                limit=int(ctx.metadata.get("retrieval_limit") or 8),
            )
        else:
            ctx.retrieved = await self.retriever.search(
                ctx.user_id,
                ctx.query,
                limit=int(ctx.metadata.get("retrieval_limit") or 8),
                source_types=source_types,
            )
        ctx.latency_ms[self.name] = (time.perf_counter() - started) * 1000
        ctx.trace.append({"component": self.name, "hits": len(ctx.retrieved)})
        return ctx


class RankerComponent(PipelineComponent):
    name = "ranker"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        started = time.perf_counter()
        from keprix.documents.reranker import rerank_chunks

        limit = int(ctx.metadata.get("rank_limit") or 5)
        ctx.ranked = rerank_chunks(ctx.query, ctx.retrieved, limit=limit)
        if ctx.ranked:
            ctx.confidence = float(ctx.ranked[0].get("rerank_score") or ctx.ranked[0].get("score") or 0.0)
        ctx.latency_ms[self.name] = (time.perf_counter() - started) * 1000
        ctx.trace.append({"component": self.name, "ranked": len(ctx.ranked), "confidence": ctx.confidence})
        return ctx


class GeneratorComponent(PipelineComponent):
    name = "generator"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        started = time.perf_counter()
        if ctx.route == "clarification":
            ctx.answer = (
                "I need a bit more detail to answer confidently. "
                "Can you specify the document source or timeframe?"
            )
        elif ctx.route == "deep_research":
            ctx.answer = (
                "Routing to deeper research because retrieval confidence is low. "
                "A research pass will gather more sources before answering."
            )
        elif ctx.ranked:
            snippets = [str(row.get("content") or "")[:200] for row in ctx.ranked[:3]]
            ctx.answer = "Based on retrieved documents: " + " ".join(snippets)
        else:
            ctx.answer = "No matching documents were found."
        ctx.cost_units += 0.01
        ctx.latency_ms[self.name] = (time.perf_counter() - started) * 1000
        ctx.trace.append({"component": self.name, "route": ctx.route})
        return ctx


class AnswerBuilderComponent(PipelineComponent):
    name = "answer_builder"

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        started = time.perf_counter()
        ctx.citations = [
            {
                "source": str(row.get("source") or "unknown"),
                "snippet": str(row.get("content") or "")[:240],
                "score": float(row.get("rerank_score") or row.get("score") or 0.0),
            }
            for row in ctx.ranked
        ]
        if ctx.citations and ctx.route == "direct_answer":
            refs = " ".join(f"[{idx + 1}] {cite['snippet']}" for idx, cite in enumerate(ctx.citations[:3]))
            ctx.answer = f"{ctx.answer} Citations: {refs}"
        ctx.latency_ms[self.name] = (time.perf_counter() - started) * 1000
        ctx.trace.append({"component": self.name, "citations": len(ctx.citations)})
        return ctx


class EvaluatorComponent(PipelineComponent):
    name = "evaluator"

    def __init__(self, evaluator: Any) -> None:
        self.evaluator = evaluator

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        started = time.perf_counter()
        report = self.evaluator.evaluate_run(
            ctx,
            pipeline_id=str(ctx.metadata.get("pipeline_id") or "default"),
        )
        ctx.metadata["evaluation"] = report.to_dict()
        ctx.latency_ms[self.name] = (time.perf_counter() - started) * 1000
        ctx.trace.append({"component": self.name, "evaluation_id": report.eval_id})
        return ctx
