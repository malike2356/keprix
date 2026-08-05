# Keprix - Prompt 83: Adopt OmniRoute; Notion Workspace Integration

## Context

OmniRoute's Notion integration allows agents to read, search, query, and write to Notion workspaces. Agents can pull context from Notion databases, save research findings to pages, and use Notion as an external knowledge store.

Keprix personas that benefit:
- **SAGE**; save research briefings directly to a Notion knowledge base
- **BEACON**; pull brand voice guidelines from Notion, save campaign plans
- **COMPASS**; query strategy databases, save decision records
- **NEXUS**; log project status to a Notion dashboard
- **CODEX**; save contract reviews to a legal workspace
- All personas; use Notion as persistent cross-session memory

## Reference Clone

`planning/competitor-research/agents-to-adopt/omniroute/`

Key source files:
```
src/lib/notion/api.ts; Notion API client (error handling, retries)
src/lib/db/notion.ts; Token storage
open-sse/mcp-server/tools/notionTools.ts; 6 MCP tools for Notion
src/app/api/settings/notion/route.ts; Settings endpoint
```

## What to Adopt

### Notion API Client

OmniRoute's client handles:
- Authentication via integration token (Bearer)
- API versioning (`Notion-Version: 2026-03-11`)
- Error classification (auth, not found, rate limit, validation, server, timeout)
- Automatic retry with exponential backoff (3 attempts)
- Rate limit handling (respects `retry-after` header)
- 55-second timeout with abort controller
- Error message sanitisation (removes file paths from error messages)

### Notion MCP Tools

Six tools wrapped as MCP-compatible functions:

| Tool | Description | Scope |
|------|-------------|-------|
| `notion_search` | Search pages and databases by text | `read:notion` |
| `notion_get_page` | Get page content and metadata by ID | `read:notion` |
| `notion_list_block_children` | List block children of a page/block | `read:notion` |
| `notion_query_database` | Query database with filters and sorts | `read:notion` |
| `notion_get_database` | Get database schema and metadata | `read:notion` |
| `notion_append_blocks` | Append blocks to a page (max 100 per request) | `write:notion` |

## Files To Create

```text
src/keprix/integrations/notion/
  __init__.py
  client.py              # Notion API client (adopt from notion/api.ts)
  errors.py              # Error classification (NotionAuthError, NotionRateLimitError, etc.)
  retry.py               # Retry logic with exponential backoff
  token_store.py         # Secure token storage
  
  tools/
    __init__.py
    search.py            # Search pages and databases
    get_page.py          # Get page content
    list_blocks.py       # List block children
    query_database.py    # Query database
    get_database.py      # Get database metadata
    append_blocks.py     # Append blocks to page
    registry.py          # Tool registration with MCP

  workspace/
    __init__.py
    sync.py              # Bi-directional sync between Keprix and Notion
    context_loader.py    # Load Notion pages as agent context
    exporter.py          # Export agent findings to Notion pages
    
  templates/
    research_brief.md    # Template for research briefings → Notion
    campaign_plan.md     # Template for campaign plans → Notion
    strategy_record.md   # Template for strategy decisions → Notion
    project_status.md    # Template for project status → Notion

config/
  notion.example.yaml    # Example Notion configuration

tests/integrations/notion/
  test_client.py
  test_tools.py
  test_sync.py
  test_context_loader.py
```

## Implementation

### Notion API Client (adopt from `notion/api.ts`)

```python
NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"
MAX_RETRIES = 3
TIMEOUT_SECONDS = 55

class NotionAuthError(Exception): ...
class NotionNotFoundError(Exception): ...
class NotionRateLimitError(Exception):
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after
class NotionValidationError(Exception): ...
class NotionServerError(Exception): ...
class NotionTimeoutError(Exception): ...


class NotionClient:
    """Notion API client with retry, rate limiting, and error handling."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = httpx.AsyncClient(
            base_url=NOTION_API_BASE,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            timeout=TIMEOUT_SECONDS,
        )
    
    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """Make a request with automatic retry and error classification."""
        
        last_error: Exception | None = None
        
        for attempt in range(MAX_RETRIES):
            try:
                response = await self.session.request(
                    method, path, json=json, params=params
                )
                
                if response.is_success:
                    return response.json()
                
                error_body = response.json()
                error = self._classify_error(response.status_code, error_body)
                
                if isinstance(error, NotionRateLimitError):
                    last_error = error
                    wait = error.retry_after + (2 ** attempt) * 0.2
                    await asyncio.sleep(wait)
                    continue
                
                if isinstance(error, NotionServerError) and attempt < MAX_RETRIES - 1:
                    last_error = error
                    await asyncio.sleep((2 ** attempt) * 0.5)
                    continue
                
                raise error
                
            except httpx.TimeoutException:
                raise NotionTimeoutError("Notion API request timed out after 55s")
            except (NotionAuthError, NotionNotFoundError, NotionValidationError):
                raise
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    last_error = e
                    await asyncio.sleep((2 ** attempt) * 0.5)
                    continue
                raise
        
        raise last_error or NotionServerError("Exhausted all retries")
    
    def _classify_error(self, status: int, body: dict) -> Exception:
        code = body.get("code", "unknown")
        message = self._sanitize(body.get("message", f"HTTP {status}"))
        
        if status == 401:
            return NotionAuthError(message)
        if status == 403:
            return NotionAuthError(f"Access denied: {message}")
        if status == 404:
            return NotionNotFoundError(message)
        if status == 409:
            return NotionValidationError(f"Conflict: {message}")
        if status == 429:
            retry_after = self._parse_retry_after(message)
            return NotionRateLimitError(message, retry_after)
        if status == 400:
            return NotionValidationError(message)
        if status >= 500:
            return NotionServerError(message)
        return NotionValidationError(message)
    
    def _sanitize(self, msg: str) -> str:
        """Remove file paths and stack traces from error messages."""
        import re
        msg = re.sub(r'\s+at\s+\S+', '', msg)
        msg = re.sub(r'/[\w/.-]+\.[a-z]+:\d+', '', msg)
        return msg[:4096]
    
    def _parse_retry_after(self, message: str) -> int:
        import re
        match = re.search(r'retry after (\d+)', message, re.IGNORECASE)
        if match:
            return int(match.group(1))
        match = re.search(r'(\d+)', message)
        return int(match.group(1)) if match else 1
    
    # --- API Methods ---
    
    async def search(self, query: str, start_cursor: str | None = None, page_size: int = 20) -> dict:
        body = {
            "query": query,
            "page_size": min(page_size, 100),
            "filter": {"value": "page", "property": "object"},
        }
        if start_cursor:
            body["start_cursor"] = start_cursor
        return await self._request("POST", "/search", json=body)
    
    async def get_page(self, page_id: str) -> dict:
        return await self._request("GET", f"/pages/{page_id}")
    
    async def list_block_children(self, block_id: str, start_cursor: str | None = None, page_size: int = 50) -> dict:
        params = {"page_size": min(page_size, 100)}
        if start_cursor:
            params["start_cursor"] = start_cursor
        return await self._request("GET", f"/blocks/{block_id}/children", params=params)
    
    async def query_database(
        self,
        database_id: str,
        filter: dict | None = None,
        sorts: list | None = None,
        start_cursor: str | None = None,
        page_size: int = 50,
    ) -> dict:
        body: dict = {"page_size": min(page_size, 100)}
        if filter:
            body["filter"] = filter
        if sorts:
            body["sorts"] = sorts
        if start_cursor:
            body["start_cursor"] = start_cursor
        return await self._request("POST", f"/databases/{database_id}/query", json=body)
    
    async def get_database(self, database_id: str) -> dict:
        return await self._request("GET", f"/databases/{database_id}")
    
    async def append_blocks(self, block_id: str, children: list, after: str | None = None) -> dict:
        body: dict = {"children": children[:100]}
        if after:
            body["after"] = after
        return await self._request("PATCH", f"/blocks/{block_id}/children", json=body)
```

### MCP Tool Registration

```python
# src/keprix/integrations/notion/tools/registry.py

NOTION_TOOLS = [
    Tool(
        name="notion_search",
        description="Search pages and databases in Notion by text query. Returns matching page titles, IDs, and URL.",
        scopes=["read:notion"],
        parameters={
            "query": {"type": "string", "description": "Search query text"},
            "page_size": {"type": "integer", "default": 20, "maximum": 100},
            "start_cursor": {"type": "string", "description": "Pagination cursor"},
        },
        handler="search_pages",
    ),
    Tool(
        name="notion_get_page",
        description="Get the content and metadata of a Notion page by its ID.",
        scopes=["read:notion"],
        parameters={
            "page_id": {"type": "string", "description": "Notion page ID (32-char hex or UUID)"},
        },
        handler="get_page",
    ),
    Tool(
        name="notion_list_block_children",
        description="List all block children of a Notion block or page.",
        scopes=["read:notion"],
        parameters={
            "block_id": {"type": "string", "description": "Block ID to fetch children from"},
            "page_size": {"type": "integer", "default": 50, "maximum": 100},
            "start_cursor": {"type": "string", "description": "Pagination cursor"},
        },
        handler="list_block_children",
    ),
    Tool(
        name="notion_query_database",
        description="Query a Notion database with optional filters and sorts.",
        scopes=["read:notion"],
        parameters={
            "database_id": {"type": "string", "description": "Notion database ID"},
            "filter": {"type": "object", "description": "Notion API filter object"},
            "sorts": {"type": "array", "description": "Notion API sort array"},
            "page_size": {"type": "integer", "default": 50, "maximum": 100},
            "start_cursor": {"type": "string", "description": "Pagination cursor"},
        },
        handler="query_database",
    ),
    Tool(
        name="notion_get_database",
        description="Get metadata and schema of a Notion database by its ID.",
        scopes=["read:notion"],
        parameters={
            "database_id": {"type": "string", "description": "Notion database ID"},
        },
        handler="get_database",
    ),
    Tool(
        name="notion_append_blocks",
        description="Append block children to an existing Notion block or page. Maximum 100 blocks per request.",
        scopes=["write:notion"],
        parameters={
            "block_id": {"type": "string", "description": "Target block or page ID to append to"},
            "children": {"type": "array", "description": "Array of block objects to append"},
            "after": {"type": "string", "description": "Block ID to append after"},
        },
        handler="append_blocks",
    ),
]
```

### Context Loader; Pull Notion into Agent Context

```python
class NotionContextLoader:
    """Loads Notion pages as agent context before tool execution."""
    
    async def load_context(
        self,
        page_ids: list[str] | None = None,
        database_query: DatabaseQuery | None = None,
    ) -> list[ContextBlock]:
        """Load pages from Notion and convert to agent context blocks."""
        
        client = NotionClient(await self.token_store.get())
        context = []
        
        # Load specific pages
        if page_ids:
            for page_id in page_ids:
                page = await client.get_page(page_id)
                blocks = await self._fetch_all_blocks(client, page_id)
                context.append(ContextBlock(
                    source=f"notion://{page_id}",
                    title=self._extract_title(page),
                    content=self._blocks_to_markdown(blocks),
                ))
        
        # Query database
        if database_query:
            results = await client.query_database(
                database_query.database_id,
                filter=database_query.filter,
                sorts=database_query.sorts,
            )
            for page in results.get("results", []):
                context.append(ContextBlock(
                    source=f"notion://{page['id']}",
                    title=self._extract_title(page),
                    content=self._page_to_summary(page),
                ))
        
        return context
    
    def _blocks_to_markdown(self, blocks: list[dict]) -> str:
        """Convert Notion blocks to markdown for LLM context."""
        md = []
        for block in blocks:
            block_type = block.get("type", "")
            content = block.get(block_type, {})
            
            if block_type == "paragraph":
                text = self._rich_text_to_plain(content.get("rich_text", []))
                if text.strip():
                    md.append(f"{text}\n")
            elif block_type == "heading_1":
                text = self._rich_text_to_plain(content.get("rich_text", []))
                md.append(f"# {text}\n")
            elif block_type == "heading_2":
                text = self._rich_text_to_plain(content.get("rich_text", []))
                md.append(f"## {text}\n")
            elif block_type == "heading_3":
                text = self._rich_text_to_plain(content.get("rich_text", []))
                md.append(f"### {text}\n")
            elif block_type == "bulleted_list_item":
                text = self._rich_text_to_plain(content.get("rich_text", []))
                md.append(f"- {text}\n")
            elif block_type == "numbered_list_item":
                text = self._rich_text_to_plain(content.get("rich_text", []))
                md.append(f"1. {text}\n")
            elif block_type == "code":
                text = self._rich_text_to_plain(content.get("rich_text", []))
                lang = content.get("language", "")
                md.append(f"```{lang}\n{text}\n```\n")
            elif block_type == "to_do":
                text = self._rich_text_to_plain(content.get("rich_text", []))
                checked = "x" if content.get("checked") else " "
                md.append(f"- [{checked}] {text}\n")
        
        return "".join(md)
```

### Exporter; Save Agent Findings to Notion

```python
class NotionExporter:
    """Exports agent findings, reports, and decisions to Notion pages."""
    
    TEMPLATES = {
        "research_brief": "templates/research_brief.md",
        "campaign_plan": "templates/campaign_plan.md",
        "strategy_record": "templates/strategy_record.md",
        "project_status": "templates/project_status.md",
    }
    
    async def export_findings(
        self,
        parent_page_id: str,
        title: str,
        content: str,
        template: str = "research_brief",
    ) -> str:
        """Export agent findings as a new Notion page."""
        
        client = NotionClient(await self.token_store.get())
        
        # Build page blocks from content
        blocks = self._markdown_to_blocks(content)
        
        # Create page
        page = await client._request("POST", "/pages", json={
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": {"title": [{"text": {"content": title}}]},
            },
            "children": blocks,
        })
        
        return page["url"]
    
    async def append_to_page(self, page_id: str, content: str) -> None:
        """Append content to an existing page."""
        
        client = NotionClient(await self.token_store.get())
        blocks = self._markdown_to_blocks(content)
        
        # Append in chunks of 100
        for i in range(0, len(blocks), 100):
            await client.append_blocks(page_id, blocks[i:i+100])
    
    def _markdown_to_blocks(self, md: str) -> list[dict]:
        """Convert markdown text to Notion block objects."""
        blocks = []
        lines = md.split("\n")
        
        for line in lines:
            if line.startswith("# "):
                blocks.append(self._heading_block(1, line[2:]))
            elif line.startswith("## "):
                blocks.append(self._heading_block(2, line[3:]))
            elif line.startswith("### "):
                blocks.append(self._heading_block(3, line[4:]))
            elif line.startswith("- "):
                blocks.append(self._bulleted_block(line[2:]))
            elif line.strip():
                blocks.append(self._paragraph_block(line))
        
        return blocks
```

### Agent Integration

```python
# Agents can use Notion as context source and output target:

@agent_tool(name="load_notion_context")
async def load_notion_context(page_ids: list[str] | None = None) -> str:
    """Load Notion pages as context for this task."""
    loader = NotionContextLoader()
    context = await loader.load_context(page_ids=page_ids)
    return "\n\n".join(b.content for b in context)

@agent_tool(name="save_to_notion")
async def save_to_notion(parent_page: str, title: str, content: str, template: str = "research_brief") -> str:
    """Save agent output to a Notion page."""
    exporter = NotionExporter()
    url = await exporter.export_findings(parent_page, title, content, template)
    return f"Saved to Notion: {url}"
```

### Configuration

```yaml
# config/notion.yaml
notion:
  enabled: false                    # Enable via env: KEPRIX_NOTION_ENABLED=true
  integration_token_env: "NOTION_INTEGRATION_TOKEN"
  default_parent_page_id: ""        # Default page to create sub-pages under
  
  context_sources:
    - page_id: ""                   # Page to auto-load as context on every session
    - database_id: ""               # Database to query for context
    
  auto_export:
    enabled: false                  # Auto-export agent findings to Notion
    persona_pages:                  # Per-persona export targets
      sage: ""                      # Research briefings → this page
      beacon: ""                    # Campaign plans → this page
      compass: ""                   # Strategy records → this page
      codex: ""                     # Legal reviews → this page
```

## Safety; Non-Breaking

1. **Notion integration disabled by default.** Enable via `KEPRIX_NOTION_ENABLED=true`.
2. **Token validation on startup.** If token is invalid, tools return clear error, don't crash.
3. **Write operations require confirmation.** Append blocks triggers approval gate.
4. **Read operations are informational.** No approval needed for search/get_page/query.
5. **Rate limit handling built in.** Automatic backoff, never hammer the API.
6. **Context loading is lazy.** Only fetches on explicit agent request, not every turn.

## Verification

- [ ] Notion client connects with valid integration token
- [ ] Search returns matching pages and databases
- [ ] Get page returns full page content
- [ ] List block children returns correct block tree
- [ ] Query database returns filtered and sorted results
- [ ] Append blocks adds content to target page (max 100 per request)
- [ ] Rate limit hits trigger automatic retry with backoff
- [ ] Auth errors return clear message without crashing
- [ ] Context loader converts Notion blocks to usable markdown
- [ ] Exporter creates new page with agent findings
- [ ] Bi-directional sync works (Notion → agent → Notion roundtrip)
- [ ] Notion tools disabled when env flag not set
- [ ] Token stored securely, never logged
- [ ] Tests pass for all modules
