# Keprix - Prompt 269: Graphiti MCP + brain ingest bridge

**Series:** Chase five tools adoption **267-272**.  
**Master reference:** `../prompts-archive/ref-266-chase-five-tools-adoption-master-reference.md`  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

**Graphiti integration** as an optional MCP bridge plus **native ingest jobs** that feed Keprix brain graph work (Chase "Graphiti" pattern).

Capabilities:

| Capability | Description |
| --- | --- |
| MCP catalog entry | Connect `GRAPHITI_MCP_URL` Graphiti server |
| Ingest jobs | Push session exports, research reports, vault notes into graph |
| Retrieval hook | Agent tool `graphiti_query` + fallback to native graph API (**246+**) |
| Sync status | Job ledger with node/edge counts |

**Non-goals:**

- Replace ChromaDB / vector RAG with graph-only memory
- Ship Graphiti server inside Keprix core
- Block agent runs when Graphiti offline (degrade gracefully)

---

## 2. Already built (do not reimplement)

| Area | Location |
| --- | --- |
| MCP URL hint | `profile_distribution.py` (`GRAPHITI_MCP_URL`) |
| Hindsight MCP patterns | existing MCP catalog wiring |
| Brain graph drafts | prompts **246-254** (parallel native API) |
| RAG / embeddings | **230** ML series |

---

## 3. Architecture

```text
Settings: GRAPHITI_MCP_URL
        |
        v
graphiti_bridge.py (MCP client)
        |
        v
graphiti_ingest_service.py
  - ingest from research report / session / vault file
        |
        v
IngestJob ledger + optional native graph_edges table (246+)
        |
        v
graphiti_query tool (agent) + /api/brain/graphiti/*
```

---

## 4. Data model

```python
@dataclass
class GraphitiIngestJob:
    job_id: str
    source_type: str         # research | session | vault_file | manual
    source_ref: str
    status: str              # queued | running | done | failed
    nodes_added: int
    edges_added: int
    graphiti_episode_id: str | None
    error: str | None
    created_at: str
```

Persist under `{KEPRIX_HOME}/brain/graphiti/jobs/{job_id}.json`.

---

## 5. MCP tools (expected surface)

Document and implement client for Graphiti MCP tools (adapt to upstream names):

| Tool | Purpose |
| --- | --- |
| `add_episode` / equivalent | Ingest text corpus |
| `search` / `query` | Retrieve facts and relationships |
| `get_entity` | Fetch node detail |

If upstream differs, wrap in `graphiti_bridge.py` with stable Keprix names.

---

## 6. Agent tool

**`graphiti_query`**

```json
{
  "query": "What did we learn about competitor X?",
  "max_results": 10,
  "include_sources": true
}
```

Returns structured hits with citations. When MCP unavailable, return clear error suggesting native brain search if **246+** shipped.

---

## 7. API routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/brain/graphiti/status` | Connection health |
| POST | `/api/brain/graphiti/ingest` | `{ source_type, source_ref }` |
| GET | `/api/brain/graphiti/jobs` | List ingest jobs |
| GET | `/api/brain/graphiti/jobs/{id}` | Job detail |
| POST | `/api/brain/graphiti/query` | Direct query (UI debugger) |

Feature flag: `brain.graphiti.enabled`.

---

## 8. UI

`/brain/graphiti` (or section under Brain):

- Connection status card (MCP URL masked)
- Ingest form: pick research job, session, or vault file
- Job table with counts
- Query debugger textarea

Hooks on **268** report view and **267** video manifest: "Ingest to graph".

---

## 9. Files to create

```
src/keprix/brain/
  graphiti_bridge.py
  graphiti_ingest_service.py
  graphiti_job_store.py

src/keprix/tools/
  graphiti_query.py

src/keprix/api/
  graphiti_routes.py

frontend/src/app/(workspace)/brain/graphiti/page.tsx

docs/features/graphiti-bridge.md

tests/brain/
  test_graphiti_bridge_mock.py
  test_graphiti_ingest_service.py
  test_graphiti_query_tool.py
```

Register tool in `toolsets.py` under research/brain profile.

---

## 10. Acceptance criteria

- With mock MCP, ingest job completes and records node/edge counts.
- `graphiti_query` tool registered and returns structured JSON in tests.
- Health endpoint reports `connected | misconfigured | unreachable`.
- Ingest from a Markdown research report creates at least one episode call (mocked).
- Feature flag disables routes and tool when off.
- `GRAPHITI_MCP_URL` documented in `.env.example` and `cli-config.yaml.example`.

---

## 11. Dependencies

- **Parallel:** brain graph API **246-254**
- **Soft:** **258-259** vault for file sources
- **Feeds from:** **267** video manifests, **268** notebook reports
