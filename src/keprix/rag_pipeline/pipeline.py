"""Haystack-style RAG pipeline orchestration with playbook tracing."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from keprix.memory.rag.indexer import RagIndexer
from keprix.memory.rag.retriever import RagRetriever
from keprix.playbook.runtime import END, PlaybookGraph, PlaybookRunner, playbook_registry
from keprix.rag_pipeline.component import (
    AnswerBuilderComponent,
    CleanerComponent,
    ConverterComponent,
    EmbedderComponent,
    EvaluatorComponent,
    GeneratorComponent,
    PipelineComponent,
    PipelineContext,
    RankerComponent,
    RetrieverComponent,
    SplitterComponent,
)
from keprix.rag_pipeline.document_store import DocumentStore, create_document_store
from keprix.rag_pipeline.evaluator import EvaluationStore, PipelineEvaluator
from keprix.rag_pipeline.router import PipelineRouter


@dataclass
class PipelineRunResult:
    run_id: str
    pipeline_id: str
    playbook_run_id: str | None
    context: PipelineContext
    evaluation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "pipeline_id": self.pipeline_id,
            "playbook_run_id": self.playbook_run_id,
            "evaluation_id": self.evaluation_id,
            **self.context.to_dict(),
        }


class RagPipeline:
    def __init__(
        self,
        pipeline_id: str,
        *,
        store_kind: str = "memory",
        store: DocumentStore | None = None,
        indexer: RagIndexer | None = None,
        evaluator: PipelineEvaluator | None = None,
        router: PipelineRouter | None = None,
    ) -> None:
        self.pipeline_id = pipeline_id
        self.indexer = indexer or RagIndexer()
        self.store = store or create_document_store(store_kind, indexer=self.indexer)
        self.retriever = RagRetriever(indexer=self.indexer)
        self.evaluator = evaluator or PipelineEvaluator()
        self.router = router or PipelineRouter()

    def ingest_components(self) -> list[PipelineComponent]:
        return [
            ConverterComponent(),
            CleanerComponent(),
            SplitterComponent(),
            EmbedderComponent(),
        ]

    def query_components(self) -> list[PipelineComponent]:
        return [
            RetrieverComponent(self.retriever),
            RankerComponent(),
            PipelineRouter(
                confidence_threshold=self.router.confidence_threshold,
                cost_limit=self.router.cost_limit,
                blocked_terms=self.router.blocked_terms,
            ),
            GeneratorComponent(),
            AnswerBuilderComponent(),
            EvaluatorComponent(self.evaluator),
        ]

    async def _run_components(
        self,
        components: list[PipelineComponent],
        ctx: PipelineContext,
        *,
        trace_playbook: bool = True,
    ) -> tuple[PipelineContext, str | None]:
        for component in components:
            started = time.perf_counter()
            ctx = await component.run(ctx)
            ctx.trace.append(
                {
                    "playbook_node": component.name,
                    "duration_ms": (time.perf_counter() - started) * 1000,
                }
            )
        playbook_run_id = None
        if trace_playbook:
            playbook_run_id = await self._register_playbook_trace(components, ctx)
        return ctx, playbook_run_id

    async def _register_playbook_trace(
        self,
        components: list[PipelineComponent],
        ctx: PipelineContext,
    ) -> str:
        graph = PlaybookGraph(f"rag-pipeline-{self.pipeline_id}")

        def pass_through(state: dict[str, Any], node_name: str = "") -> dict[str, Any]:
            return {**state, "last_node": node_name}

        for component in components:
            name = component.name
            graph.add_node(name, lambda state, n=name: pass_through(state, n))
        names = [component.name for component in components]
        for index, name in enumerate(names):
            target = names[index + 1] if index + 1 < len(names) else END
            graph.add_edge(name, target)

        runner = PlaybookRunner(graph.compile())
        run = await runner.execute_inline({"pipeline_id": self.pipeline_id, "user_id": ctx.user_id})
        playbook_registry.register(run, runner)
        return run.run_id

    async def ingest(
        self,
        *,
        user_id: str,
        source_type: str,
        source_id: str,
        content: str,
    ) -> PipelineRunResult:
        ctx = PipelineContext(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            raw_content=content,
        )
        ctx, playbook_run_id = await self._run_components(self.ingest_components(), ctx)
        chunk_count = await self.store.ingest(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            content=content,
            chunks=ctx.chunks,
            embeddings=ctx.embeddings,
        )
        ctx.metadata["ingested_chunks"] = chunk_count
        return PipelineRunResult(
            run_id=str(uuid.uuid4()),
            pipeline_id=self.pipeline_id,
            playbook_run_id=playbook_run_id,
            context=ctx,
        )

    async def query(
        self,
        *,
        user_id: str,
        question: str,
        source_types: list[str] | None = None,
        hybrid: bool = True,
    ) -> PipelineRunResult:
        ctx = PipelineContext(
            user_id=user_id,
            query=question,
            metadata={
                "pipeline_id": self.pipeline_id,
                "source_types": source_types or [],
                "hybrid": hybrid,
                "retrieval_limit": 8,
                "rank_limit": 5,
            },
        )
        ctx, playbook_run_id = await self._run_components(self.query_components(), ctx)
        evaluation = ctx.metadata.get("evaluation") or {}
        return PipelineRunResult(
            run_id=str(uuid.uuid4()),
            pipeline_id=self.pipeline_id,
            playbook_run_id=playbook_run_id,
            context=ctx,
            evaluation_id=evaluation.get("eval_id"),
        )


class PipelineRegistry:
    def __init__(self) -> None:
        self._pipelines: dict[str, RagPipeline] = {}
        self._runs: dict[str, PipelineRunResult] = {}
        self.eval_store = EvaluationStore()

    def get_or_create(self, pipeline_id: str, *, store_kind: str = "memory") -> RagPipeline:
        if pipeline_id not in self._pipelines:
            evaluator = PipelineEvaluator(store=self.eval_store)
            self._pipelines[pipeline_id] = RagPipeline(
                pipeline_id,
                store_kind=store_kind,
                evaluator=evaluator,
            )
        return self._pipelines[pipeline_id]

    def save_run(self, result: PipelineRunResult) -> None:
        self._runs[result.run_id] = result

    def get_run(self, run_id: str) -> PipelineRunResult | None:
        return self._runs.get(run_id)

    def list_runs(self, pipeline_id: str | None = None, limit: int = 50) -> list[PipelineRunResult]:
        runs = list(self._runs.values())
        if pipeline_id:
            runs = [run for run in runs if run.pipeline_id == pipeline_id]
        return runs[-limit:]


_registry = PipelineRegistry()


def get_pipeline_registry() -> PipelineRegistry:
    return _registry
