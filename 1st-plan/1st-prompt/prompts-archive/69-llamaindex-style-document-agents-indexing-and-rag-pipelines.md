# keprix - Prompt 69: LlamaIndex-Style Document Agents, Indexing, and RAG Pipelines

> **Status (2026-07-05):** Implemented under `src/keprix/documents/` extending Prompt 06 RAG (`memory/rag/`). Parsing, structured extraction, index manager, hybrid query engine with citations, document agent workflow, `/api/documents/*`, `/documents` UI, and 7 tests.

## Context

Prompt 06 creates memory and RAG. This prompt expands keprix with LlamaIndex-style data connectors, document parsing, structured extraction, index management, query engines, workflow agents, and document-agent apps.

Do not duplicate Prompt 06. Extend the memory and research systems.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/llama-index/README.md
planning/agents-to-adopt/llama-index/llama-index-core
planning/agents-to-adopt/llama-index/llama-index-integrations
```

## Files To Create Or Extend

```text
backend/documents/
  __init__.py
  parser.py
  structured_extract.py
  connector_registry.py
  index_manager.py
  query_engine.py
  retriever.py
  reranker.py
  document_agent.py
  workflow.py
frontend/src/components/documents/DocumentAgentPanel.tsx
frontend/src/components/documents/IndexManagerPanel.tsx
tests/documents/test_parser.py
tests/documents/test_structured_extract.py
tests/documents/test_query_engine.py
tests/documents/test_document_agent.py
```

## Required Features

### Document Parsing

Support:

- PDF.
- Word.
- HTML.
- Markdown.
- CSV.
- JSON.
- Email export.
- Images with OCR when configured.

### Structured Extraction

Extract into typed schemas:

- Invoice.
- Contract.
- Research paper.
- Meeting notes.
- Customer ticket.
- Generic entity schema.

### Index Management

Support:

- Create index.
- Refresh index.
- Delete index.
- Inspect source coverage.
- Show stale documents.
- Explain retrieval path.

### Query Engine

Support:

- Hybrid retrieval.
- Metadata filters.
- Reranking.
- Citation snippets.
- Multi-document synthesis.
- Evidence-first answer mode.

## Acceptance Criteria

- A user can upload documents, build an index, and ask cited questions.
- Structured extraction validates outputs through typed schemas.
- Query engine explains which sources were used.
- OCR and paid parsing services are optional adapters only.
- Sensitive document content is not written to ordinary logs.

