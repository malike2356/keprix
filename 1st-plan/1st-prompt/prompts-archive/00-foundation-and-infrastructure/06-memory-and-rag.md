# keprix - Prompt 06: Memory and RAG

## Context

Sources:
- `hermes-agent/agent/memory_manager.py`, `memory_provider.py`
- `hermes-agent/plugins/memory/`
- `odysseus/mcp_servers/memory_server.py`, `routes/memory_routes.py`
- `odysseus/mcp_servers/rag_server.py`
- `core.carinaai.uk/src/memory/` - pgvector episodic store, REM consolidation
Output: `keprix/backend/memory/`

## Architecture

keprix uses a three-layer memory system:

```
Layer 1: Working Memory    - current conversation context (in-process)
Layer 2: Episodic Memory   - per-user session memories (PostgreSQL + pgvector)
Layer 3: RAG Corpus        - embedded documents, notes, emails (pgvector)
```

## Layer 1: Working Memory

Port from Hermes verbatim:
```
agent/memory_manager.py    -> backend/memory/manager.py
agent/memory_provider.py   -> backend/memory/provider.py
```

The working memory manager handles:
- Per-conversation short-term facts the agent stores with `remember` tool
- Injection into system prompt prefix at conversation start
- Automatic pruning when context window approaches limit (use `context_compressor.py`)

## Layer 2: Episodic Memory

Port `hermes-agent/plugins/memory/` verbatim to `backend/memory/episodic/`.

Supplement with the REM (Reflection and Episodic Memory) consolidation from
`core.carinaai.uk/src/memory/`. Read that TypeScript source and implement the
same consolidation logic in Python in `backend/memory/rem_consolidation.py`:
- After each session ends, run a background consolidation pass
- Extract durable facts from the conversation trajectory
- Store as embeddings in `memories` table (PostgreSQL + pgvector)
- Tag with user_id, session_id, timestamp, and topic tags
- Prune memories older than `memory_ttl_days` (default: 90, configurable)

`backend/memory/episodic/store.py` must implement:
```python
class EpisodicStore:
    async def save(self, user_id: str, content: str, metadata: dict) -> str
    async def search(self, user_id: str, query: str, limit: int = 10) -> list[Memory]
    async def delete(self, user_id: str, memory_id: str) -> None
    async def list_all(self, user_id: str) -> list[Memory]
    async def clear(self, user_id: str) -> None
```

## Layer 3: RAG

Port from Odysseus:
```
mcp_servers/rag_server.py  -> backend/memory/rag/mcp_server.py
routes/embedding_routes.py -> backend/memory/rag/embedding_routes.py
```

Implement `backend/memory/rag/indexer.py`:
- Accept: plaintext, Markdown, PDF, HTML, email, CSV
- Chunk into 512-token overlapping windows
- Embed via Gemini `text-embedding-004` (768 dims) with OpenAI fallback
- Store in `rag_chunks` table (PostgreSQL + pgvector)
- Fields: `id`, `user_id`, `source_type`, `source_id`, `chunk_index`, `content`,
  `embedding` (vector(768)), `created_at`

Implement `backend/memory/rag/retriever.py`:
- `search(user_id, query, limit=5, source_types=None)` - cosine similarity search
- `hybrid_search(user_id, query, limit=5)` - combine pgvector + keyword (tsvector)
- Return: `[{ "content": str, "source": str, "score": float }]`

## PostgreSQL Schema

Create `keprix/backend/memory/migrations/001_memory_schema.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    session_id TEXT,
    content TEXT NOT NULL,
    embedding vector(768),
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX ON memories (user_id, created_at DESC);

CREATE TABLE rag_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON rag_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX ON rag_chunks (user_id, source_type, source_id);
CREATE INDEX ON rag_chunks USING gin(to_tsvector('english', content));
```

## Odysseus Memory MCP Server

Port `odysseus/mcp_servers/memory_server.py` verbatim to
`backend/memory/mcp_server.py`. This exposes memory as an MCP server so
external MCP clients can read/write keprix memories.

## RAG Tool Integration

`backend/tools/rag_search_tool.py` must wrap the retriever and expose it as
the `rag_search` tool in the tool dispatcher. It is a service-gated tool:
only registered when `DATABASE_URL` is set and pgvector is available.

## Persona Memory (from Hermes)

Port `hermes-agent/agent/` personal memory awareness:
- `agent/prompt_builder.py` memory injection (already ported in Prompt 03)
- Ensure memory is injected at the start of every system prompt if the user
  has saved memories matching the current conversation topic

## Memory API Endpoints

`backend/api/memory_router.py` must expose:
```
GET  /api/memory/list              - list all memories for current user
POST /api/memory/save              - save a memory (content, tags)
DELETE /api/memory/{id}            - delete a memory
POST /api/memory/search            - semantic search
POST /api/memory/clear             - delete all memories for user
POST /api/rag/ingest               - ingest a document into RAG
GET  /api/rag/sources              - list RAG sources
DELETE /api/rag/source/{id}        - delete a RAG source
POST /api/rag/search               - RAG hybrid search
```

## Acceptance Criteria

- `EpisodicStore.save()` stores and `search()` retrieves with cosine similarity
- RAG indexer chunks a 2000-word document into at least 4 chunks
- `hybrid_search` returns results ranked by combined vector + keyword score
- `GET /api/memory/list` returns 200 with empty list for a new user
- `POST /api/rag/ingest` with a plain text body creates retrievable chunks
- Memory migration SQL runs without error on a clean PostgreSQL 16 instance
