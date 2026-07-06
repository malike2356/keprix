# Memory and RAG

Keprix stores conversation history and document embeddings so the agent can recall past context, search your documents, and ground responses in your own data. This is retrieval-augmented generation (RAG) built into the runtime.

## How memory works

Every conversation is stored in PostgreSQL. When a new message arrives, the agent can:

1. Pull recent conversation history from the database (short-term memory).
2. Run a vector similarity search over embedded documents and past conversations (long-term memory / RAG).
3. Inject the retrieved chunks into its context window before generating a reply.

The agent decides whether to retrieve based on the query and configured retrieval strategy.

## Components

| Component | Role |
| --- | --- |
| PostgreSQL | Stores conversation records, memory metadata, and document content |
| ChromaDB | Vector store for similarity search (optional but recommended) |
| Embedding provider | Converts text to vectors; local (FastEmbed) or cloud (OpenAI, etc.) |
| Memory API | `/api/memory/*` routes for read/write/search |

## Configuration

### Vector store

ChromaDB is the default vector backend. Set these in `.env`:

```bash
KEPRIX_CHROMADB_HOST=chromadb        # Docker service name or IP
KEPRIX_CHROMADB_PORT=8000
KEPRIX_CHROMADB_COLLECTION=keprix_memory
```

ChromaDB runs as a sidecar container in the default `docker-compose.yml`.

### Embedding provider

```bash
# Local FastEmbed (default, no API key needed)
KEPRIX_EMBEDDING_PROVIDER=fastembed
KEPRIX_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

# OpenAI embeddings
KEPRIX_EMBEDDING_PROVIDER=openai
KEPRIX_EMBEDDING_URL=https://api.openai.com/v1/embeddings
KEPRIX_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-...

# Any OpenAI-compatible embedding endpoint
KEPRIX_EMBEDDING_PROVIDER=openai_compatible
KEPRIX_EMBEDDING_URL=http://your-ollama-host:11434/v1/embeddings
KEPRIX_EMBEDDING_MODEL=nomic-embed-text
```

### Retrieval tuning

```bash
KEPRIX_MEMORY_RETRIEVAL_TOP_K=6       # Chunks retrieved per query
KEPRIX_MEMORY_SIMILARITY_THRESHOLD=0.72  # Min cosine similarity to include
KEPRIX_MEMORY_MAX_CONTEXT_TOKENS=4096    # Cap injected context
```

## Web UI (`/memory`)

- **Memory browser**: view all stored memory documents with source, date, and excerpt.
- **Search**: semantic search over all indexed content.
- **Delete**: remove individual memories or bulk-clear by source.
- **Add**: manually add a memory document (text paste or file upload).

Memory documents from chat sessions are created automatically. Documents from the Documents workspace are indexed on upload.

## Indexing documents

Any file you upload in **Workspace > Documents** is chunked and embedded automatically. The agent can then retrieve relevant passages when answering questions about your data.

Supported file types for embedding: `.txt`, `.md`, `.pdf`, `.docx`, `.csv`, `.html`.

## Memory in agent context

When the agent receives a message it will:

1. Embed the query.
2. Query ChromaDB for the top-K most similar chunks.
3. If any chunk exceeds the similarity threshold, include it in the system prompt under a `Retrieved context` block.
4. Cite source document names in the reply (configurable).

You can observe retrieved context by enabling **Debug mode** in chat settings.

## CLI

```bash
# List memory documents
python3 -m keprix.keprix_cli.main memory

# Search memory
python3 -m keprix.keprix_cli.main memory search "quarterly report"

# Delete all memory for a session
python3 -m keprix.keprix_cli.main memory delete --session <id>
```

## API

| Action | Method | Endpoint |
| --- | --- | --- |
| List memories | GET | `/api/memory` |
| Search memories | POST | `/api/memory/search` |
| Add memory | POST | `/api/memory` |
| Delete memory | DELETE | `/api/memory/{id}` |
| Bulk delete by source | DELETE | `/api/memory?source=<source>` |
| Index a document | POST | `/api/documents/{id}/index` |
| Re-index all | POST | `/api/memory/reindex` |

## Data planes and storage layout

See [Data planes](../operations/data-planes.md) for how workspace memory, research memory, and ML/analytics storage are separated.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Agent does not recall past conversations | ChromaDB not running or wrong host | Check `KEPRIX_CHROMADB_HOST`, run `docker compose ps` |
| Embedding errors on upload | Embedding provider key missing or model unavailable | Check `KEPRIX_EMBEDDING_*` and provider reachability |
| Slow retrieval | Large collection, no HNSW index | Rebuild index via `POST /api/memory/reindex`; increase ChromaDB resources |
| Retrieved context irrelevant | Similarity threshold too low | Raise `KEPRIX_MEMORY_SIMILARITY_THRESHOLD` |
| Memory browser empty after data import | Documents not re-indexed | Run `POST /api/memory/reindex` after bulk imports |

## Related

- [Documents](documents.md)
- [Chat](chat.md)
- [Deep research](research.md)
- [RAG pipelines](rag-pipelines.md)
- [Data planes](../operations/data-planes.md)
