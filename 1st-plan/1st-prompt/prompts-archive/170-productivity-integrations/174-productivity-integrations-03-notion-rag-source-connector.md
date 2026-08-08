# Keprix Prompt 174: Productivity Integrations - Notion RAG Source Connector

## Purpose

Implement the **search/index path** for Notion documented in `docs/features/rag-pipelines.md`.
Users can index Notion pages and databases into a RAG pipeline so the agent retrieves content
without calling live Notion MCP tools on every question.

Trello is **out of scope** for RAG (use MCP from prompt 172). Read architecture reference 171.
Requires prompt **172** (Notion catalog entry); prompt 173 optional but recommended for Vault tokens.

---

## Dependencies

- `src/keprix/rag_pipeline/pipeline.py`, `routes.py`, `document_store.py`.
- `frontend/src/components/rag/PipelineBuilder.tsx`, `frontend/src/lib/rag-pipeline-api.ts`.
- Env: `KEPRIX_NOTION_TOKEN` or `NOTION_TOKEN` (document both; prefer Vault in 173).
- Notion API version header: `Notion-Version: 2025-09-03` (match `skills/productivity/notion/SKILL.md`).

---

## What to build

### 1. Connector protocol

**`src/keprix/rag_pipeline/connectors/__init__.py`** (NEW package)

```python
from typing import Protocol, List, Dict, Any

class SourceConnector(Protocol):
    connector_id: str

    def list_documents(self) -> List[Dict[str, Any]]:
        """Return [{id, title, metadata}, ...]"""

    def fetch_document(self, doc_id: str) -> Dict[str, Any]:
        """Return {id, title, content, metadata} where content is plain text or markdown."""
```

**`src/keprix/rag_pipeline/connectors/registry.py`**

```python
_CONNECTORS: dict[str, type] = {}

def register_connector(connector_id: str, cls: type) -> None: ...
def get_connector(connector_id: str, **kwargs) -> SourceConnector: ...
def list_connectors() -> list[dict]: ...
```

### 2. `src/keprix/rag_pipeline/connectors/notion.py` (NEW)

```python
class NotionSourceConnector:
    connector_id = "notion"

    def __init__(self, token: str, *, page_ids: list[str] | None = None, database_ids: list[str] | None = None):
        ...
```

Behavior:

1. **Auth:** Bearer token from constructor (caller resolves env/Vault).
2. **List:** If `page_ids` / `database_ids` provided, list those only. Else `POST /v1/search`
   with `filter: { property: object, value: page | data_source }` (paginate).
3. **Fetch page:** Prefer `GET /v1/pages/{id}/markdown` when available; fallback to blocks children.
4. **Fetch database:** Query data source, fetch each row page markdown (cap rows with config
   `max_database_rows`, default 500).
5. **Rate limits:** Respect Notion 429 with exponential backoff (max 3 retries).
6. **Read-only:** No create/update/delete Notion API calls.

### 3. API routes

Extend `src/keprix/rag_pipeline/routes.py`:

```python
@router.get("/connectors")
async def list_rag_connectors():
    return {"connectors": list_connectors()}

@router.post("/ingest/notion")
async def ingest_notion_source(body: NotionIngestBody):
    """
    body: {
      pipeline_id: str,
      store_kind: str = "memory",
      page_ids?: string[],
      database_ids?: string[],
      token?: string  # optional override; else env/vault
    }
    """
```

Flow:

1. Resolve token: `body.token` or `os.environ["KEPRIX_NOTION_TOKEN"]` or `NOTION_TOKEN` or Vault key `notion_api_token` if vault integration exists from 173.
2. Instantiate `NotionSourceConnector`.
3. For each document, call existing pipeline ingest (`RagPipeline.ingest` or equivalent).
4. Return `{ run_id, documents_ingested, errors: [] }`.

### 4. Frontend: Notion source in pipeline builder

**`frontend/src/components/rag/PipelineBuilder.tsx`**

Add **Source type** select: `manual` (existing) | `notion`.

When `notion`:

- Fields: pipeline ID, store kind, multiline **Page IDs** (comma-separated), multiline **Database IDs**.
- Optional token field (password); helper text: "Leave blank to use KEPRIX_NOTION_TOKEN or Vault".
- **Ingest from Notion** button calls new `ingestNotionPipeline()` in `rag-pipeline-api.ts`.

**`frontend/src/lib/rag-pipeline-api.ts`**

```typescript
export async function ingestNotionPipeline(body: {
  pipeline_id: string;
  store_kind?: string;
  page_ids?: string[];
  database_ids?: string[];
  token?: string;
}): Promise<{ run_id: string; documents_ingested: number }>;
```

### 5. Cross-link from MCP admin

**`frontend/src/app/(workspace)/admin/mcp/page.tsx`**

On server cards where `name` is `notion` or `notion-token` and `connection_status === connected`:

- Show link button: **Index for search** -> `/rag-pipeline?source=notion`

**`frontend/src/app/(workspace)/rag-pipeline/page.tsx`**

Read `source=notion` query param; pass to `PipelineBuilder` to pre-select Notion source.

### 6. Config and env

**`.env.example`**

```bash
# Notion integration token for RAG ingestion (optional if using MCP OAuth only)
KEPRIX_NOTION_TOKEN=
```

### 7. Tests

**`src/keprix/tests/rag_pipeline/test_notion_connector.py`** (NEW)

- Mock `httpx` or `urllib` responses for search + markdown endpoints.
- `list_documents` returns expected IDs.
- `fetch_document` returns markdown content.
- `ingest_notion_source` route returns `documents_ingested` count (TestClient + mocks).

Do not call live Notion API in CI.

---

## Acceptance criteria

1. `GET /api/rag-pipeline/connectors` includes `notion` with description.
2. `POST /api/rag-pipeline/ingest/notion` with mocked API ingests at least one document.
3. Pipeline builder Notion mode calls the new endpoint and shows success message.
4. `/admin/mcp` Notion server shows **Index for search** link when connected.
5. `/rag-pipeline?source=notion` opens builder with Notion pre-selected.
6. Connector performs no write operations to Notion (grep for POST/PATCH/DELETE to api.notion.com in connector module; only GET/POST search/query allowed).
7. All new tests pass.

---

## What this prompt does NOT do

- Confluence or other RAG sources (future prompt).
- Trello indexing.
- Scheduled/cron re-sync (manual ingest only; cron can be a follow-up).
- Operator documentation (prompt 176).
