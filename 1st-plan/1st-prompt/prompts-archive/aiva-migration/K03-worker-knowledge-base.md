# K03: Worker Knowledge Base on Keprix

**Status: COMPLETED 2026-08-07**

**What was built:**
- Package `keprix/worker_kb/` (sqlite metadata store, RAG service via RagIndexer/RagRetriever, inject helper, bootstrap)
- Alembic `025_worker_knowledge_base` (`worker_knowledge_bases`, `worker_knowledge_entries`)
- Per-worker RAG namespace `worker:{workspace_id}:{worker_id}` (isolation)
- Tools toolset `worker_kb`: `kb_add_entry`, `kb_search`, `kb_list_entries`, `kb_delete_entry`, `kb_toggle_entry`, `kb_get_context`
- Carina agent loop auto-inject: `CarinaAgentBridge.run(worker_id=...)` + `POST /carina/agent/run` body field `worker_id`
- Tests: `tests/tools/test_worker_knowledge_base.py` (7 passed)

**Phase:** 2 (Features)
**Priority:** P1
**Depends on:** K01 (agent contract working)
**Target time:** 8 hours
**Location:** Keprix

## What This Builds

Per-worker knowledge base backed by Keprix pgvector memory. Workers get document upload, FAQ storage, and semantic search retrieval. This replaces Carina's JSONL-based memory with vector search that returns relevant knowledge at query time.

## Why Keprix pgvector is Better

- Carina's JSONL: linear scan. 500 FAQ entries = slow, low relevance.
- Keprix pgvector: semantic search. Find the right FAQ even when the user's question uses different words.
- Agent loop injects relevant knowledge automatically before responding.
- Multi-worker isolation: each worker has its own namespace in the vector store.

## Data Model

```sql
CREATE TABLE worker_knowledge_bases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'Default',
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(workspace_id, worker_id, name)
);

CREATE TABLE worker_knowledge_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_base_id UUID REFERENCES worker_knowledge_bases(id) ON DELETE CASCADE,
    entry_type TEXT NOT NULL,  -- 'document', 'faq', 'instruction'
    title TEXT,
    content TEXT NOT NULL,
    source TEXT,               -- 'upload', 'manual', 'agent_learned'
    source_file TEXT,          -- original filename if uploaded
    token_count INTEGER,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- pgvector embedding table (Keprix already has this infrastructure)
-- worker_knowledge_entries get chunked and embedded
-- Each chunk links back to worker_knowledge_entries.id
```

## Keprix Tools

| Tool | Purpose |
|---|---|
| `kb_add_entry` | Add document, FAQ, or instruction to worker KB |
| `kb_search` | Semantic search across worker KB (returns top 5 chunks) |
| `kb_list_entries` | List all entries for a worker |
| `kb_delete_entry` | Remove an entry |
| `kb_toggle_entry` | Enable/disable an entry without deleting |
| `kb_get_context` | Get all enabled entries as formatted context string |

## Agent Loop Integration

When a user messages an Aiva worker:

1. Agent receives message
2. Agent calls `kb_search(query=user_message, worker_id=...)`
3. Top 5 relevant chunks injected into system prompt as context
4. Agent responds using that context
5. If agent learns something new during conversation, calls `kb_add_entry` to store it

## Acceptance Criteria

- [x] Document uploaded -> chunked -> embedded -> searchable
- [x] FAQ entry added -> returns in relevant searches
- [x] Semantic search finds correct answer even with different wording
- [x] Worker A cannot search Worker B's knowledge base
- [x] Agent auto-injects relevant KB context before responding
- [x] Entry disablement removes it from search results
