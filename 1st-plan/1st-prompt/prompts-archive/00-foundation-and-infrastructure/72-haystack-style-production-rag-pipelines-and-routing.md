# keprix - Prompt 72: Haystack-Style Production RAG Pipelines and Routing

> **Status (2026-07-05):** Implemented `src/keprix/rag_pipeline/` with modular components, routing, document stores, evaluation, deployment checks, `/api/rag-pipeline/*`, `/rag-pipeline` UI, and 9 tests.

## Context

Adopt Haystack's production RAG strengths: modular pipelines, explicit components, retrievers, rankers, routers, generators, document stores, evaluation, and deployment confidence.

This extends Prompts 06, 12, 40, 70, and 101.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/haystack/README.md
planning/agents-to-adopt/haystack/haystack
```

## Files To Create Or Extend

```text
backend/rag_pipeline/
  __init__.py
  component.py
  pipeline.py
  router.py
  retriever_component.py
  ranker_component.py
  generator_component.py
  document_store.py
  evaluator.py
  deployment.py
frontend/src/components/rag/PipelineBuilder.tsx
frontend/src/components/rag/PipelineRunViewer.tsx
tests/rag_pipeline/test_pipeline.py
tests/rag_pipeline/test_router.py
tests/rag_pipeline/test_evaluator.py
```

## Required Features

### Pipeline Components

Create explicit components:

- Converter.
- Cleaner.
- Splitter.
- Embedder.
- Retriever.
- Ranker.
- Router.
- Generator.
- Answer builder.
- Evaluator.

### Routing

Support routing by:

- Query type.
- Language.
- Document source.
- Confidence.
- Cost limit.
- Safety policy.

### Document Stores

Support:

- In-memory test store.
- SQLite store.
- Postgres store.
- pgvector store.
- Optional external vector stores.

### Evaluation

Evaluate:

- Retrieval precision.
- Citation faithfulness.
- Answer completeness.
- Hallucination risk.
- Latency.
- Cost.

## Acceptance Criteria

- A pipeline can ingest documents and answer with citations.
- Pipeline runs are traceable as playbook nodes.
- Low confidence routes to clarification or deeper research.
- Evaluation results are stored and visible in UI.
- External services are optional adapters, not required dependencies.

