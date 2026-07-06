# RAG pipelines

RAG pipelines (Retrieval-Augmented Generation pipelines) let you build and run custom data ingestion, chunking, embedding, and retrieval flows. Where the [Memory](memory.md) feature gives you an always-on document store for agent context, RAG pipelines give you explicit control over how documents are processed, indexed, and retrieved.

## When to use RAG pipelines vs memory

| Scenario | Use |
| --- | --- |
| Index your own docs, knowledge base, or codebase | RAG pipelines |
| Automatically add conversation context | Memory |
| Incremental ingestion from a data source (S3, Notion, Confluence) | RAG pipelines |
| Agent needs to search a bounded corpus precisely | RAG pipelines |
| Agent needs to remember what you told it last week | Memory |
| Custom chunking strategy or embedding model per corpus | RAG pipelines |

RAG pipelines and memory are complementary. A pipeline can feed into the memory store; the agent uses both.

## Pipeline anatomy

A pipeline has three stages:

1. **Source** - where documents come from: file upload, URL crawl, S3 bucket, Notion, Confluence, or a custom connector.
2. **Transform** - how documents are cleaned and split: chunk size, overlap, Markdown headings split, code-aware splitter, or custom transform.
3. **Index** - where embeddings are stored and how they are queried: ChromaDB (default), Qdrant, Weaviate, or pgvector.

Each pipeline has a **name**, a **schedule** (on-demand, cron, or event-triggered), and a **collection** (the target index that agents can query).

## Web UI (`/rag-pipelines`)

1. Click **New pipeline**.
2. Name the pipeline and pick a target collection.
3. Configure the source (file upload or connector).
4. Configure the transform (chunk size 256-4096 tokens, overlap 0-20%).
5. Configure the index (default: ChromaDB with `all-minilm-l6-v2` embeddings).
6. Click **Save and run**.

The pipeline status shows document count, embedding count, last-run time, and any errors.

## Sources

### File upload

Accepts PDF, DOCX, Markdown, plain text, and HTML. Uploaded files are chunked and indexed immediately.

### URL crawl

```yaml
source:
  type: url_crawl
  start_url: https://docs.example.com
  max_pages: 200
  include_patterns:
    - https://docs.example.com/api/**
  exclude_patterns:
    - https://docs.example.com/blog/**
```

### S3

```bash
KEPRIX_RAG_S3_BUCKET=my-knowledge-base
KEPRIX_RAG_S3_PREFIX=docs/
KEPRIX_RAG_S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

### Notion source connector

Notion is supported as a **read-only RAG source** via `NotionSourceConnector` in `src/keprix/rag_pipeline/connectors/notion.py`. This indexes pages and databases for search; it does not replace live Notion MCP for create/update operations.

**Operator guide:** [Notion and Trello productivity integrations](../integrations/productivity-notion-trello.md#search-notion-with-rag)

**Token:**

```bash
KEPRIX_NOTION_TOKEN=secret_...
```

**UI:** `/rag-pipeline?source=notion` (pre-selects Notion source in the pipeline builder). From `/admin/mcp`, connected Notion servers link **Index for search**.

**API:**

| Action | Method | Endpoint |
| --- | --- | --- |
| List connectors | GET | `/api/rag-pipeline/connectors` |
| Ingest from Notion | POST | `/api/rag-pipeline/ingest/notion` |
| Query pipeline | POST | `/api/rag-pipeline/query` (use `source_types: ["notion"]`) |

Example ingest body:

```json
{
  "pipeline_id": "production-default",
  "store_kind": "memory",
  "page_ids": ["page-id-optional"],
  "database_ids": []
}
```

Share target pages with your Notion integration before ingest. See the productivity guide for troubleshooting 404 responses.

### Confluence

```bash
KEPRIX_CONFLUENCE_URL=https://myorg.atlassian.net
KEPRIX_CONFLUENCE_USER=user@example.com
KEPRIX_CONFLUENCE_API_TOKEN=...
```

### Custom connector

Implement the `SourceConnector` protocol in Python and register it:

```python
from keprix.rag_pipeline.connectors.registry import register_connector

class MyCRMConnector:
    connector_id = "my-crm"
    ...

register_connector("my-crm", MyCRMConnector, description="My CRM read-only source")
```

Built-in connectors are listed at `GET /api/rag-pipeline/connectors` (includes `notion`).

## Transform configuration

```yaml
transform:
  chunk_size: 512          # tokens
  chunk_overlap: 50        # tokens
  splitter: recursive      # or: heading, sentence, code, fixed
  clean:
    strip_html: true
    normalise_whitespace: true
    remove_urls: false
```

`splitter: code` uses AST-aware splitting for Python, TypeScript, and JavaScript source files (preserves function and class boundaries).

## Index configuration

```yaml
index:
  backend: chromadb        # or: qdrant, weaviate, pgvector
  collection: my-docs
  embedding_model: all-minilm-l6-v2   # or: text-embedding-3-small, etc.
  distance: cosine         # or: l2, ip
```

See [Memory configuration](memory.md#configuration) for backend connection env vars.

## Scheduling

```yaml
schedule:
  type: cron
  expression: "0 2 * * *"   # daily at 2am
```

Or trigger on webhook: POST `/api/rag/pipelines/{id}/trigger`.

## Using a collection in an agent

Once indexed, agents can search a collection in chat:

```
/search my-docs "authentication flow"
```

Or reference it in a playbook step:

```yaml
  - id: search_docs
    type: agent_task
    prompt: "Search the my-docs collection for information about authentication"
    rag_collections: [my-docs]
    output_key: doc_results
```

## API

| Action | Method | Endpoint |
| --- | --- | --- |
| List pipelines | GET | `/api/rag/pipelines` |
| Create pipeline | POST | `/api/rag/pipelines` |
| Update pipeline | PUT | `/api/rag/pipelines/{id}` |
| Delete pipeline | DELETE | `/api/rag/pipelines/{id}` |
| Run pipeline | POST | `/api/rag/pipelines/{id}/run` |
| Trigger (webhook) | POST | `/api/rag/pipelines/{id}/trigger` |
| List collections | GET | `/api/rag/collections` |
| Search collection | POST | `/api/rag/collections/{name}/search` |
| Delete collection | DELETE | `/api/rag/collections/{name}` |

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Pipeline stuck indexing | Embedding model not loaded | Check backend logs; `KEPRIX_EMBEDDING_MODEL` must match an available model |
| Searches return irrelevant results | Chunk size too large | Reduce `chunk_size` to 256-512 for factual Q&A |
| Notion connector auth fails | Token expired | Regenerate integration token at notion.so/profile/integrations |
| S3 permission denied | IAM policy missing `s3:GetObject` | Add the policy to the IAM user or role |

## Related

- [Memory and RAG](memory.md)
- [Notion and Trello productivity integrations](../integrations/productivity-notion-trello.md)
- [Deep research](research.md)
- [Playbooks](playbooks.md)
- [Configuration: environment variables](../configuration/environment-variables.md)
