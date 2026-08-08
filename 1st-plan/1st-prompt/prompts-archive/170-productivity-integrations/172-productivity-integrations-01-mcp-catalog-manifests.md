# Keprix Prompt 172: Productivity Integrations - MCP Catalog and Manifests

## Purpose

Add **Notion** (OAuth hosted + token stdio) and **Trello** (community stdio MCP) to Keprix as
first-class catalog entries. After this prompt, users can add both from `/admin/mcp` browse
catalog or via `keprix mcp install`, without hand-editing `config.yaml`.

Read `prompts-archive/ref-171-productivity-notion-trello-architecture-reference.md` before building.

---

## Dependencies

- Autonomous MCP pack (158-161) complete: `autonomous_mcp_catalog.py`, `mcp_admin_routes.py`,
  `/admin/mcp` browse tab.
- `src/keprix/keprix_cli/mcp_catalog.py` and `optional-mcps/` manifest pattern (`linear`, `n8n`).
- Prompt 170 may still be in queue; this prompt does not conflict with skeleton loading.

---

## What to build

### 1. Extend `autonomous_mcp_catalog.py`

Add three entries after the existing `slack` entry (before `google-maps`):

**`notion`** (hosted OAuth):

```python
{
    "key": "notion",
    "label": "Notion",
    "description": "Read and write Notion pages and databases via the official hosted MCP.",
    "transport": "http",
    "url": "https://mcp.notion.com/mcp",
    "required_env": [],
    "auth_type": "oauth",
    "capability_tags": ["notion", "productivity", "notes", "database", "wiki", "pages"],
    "homepage": "https://developers.notion.com/guides/mcp/get-started-with-mcp",
    "auto_spawnable": False,
},
```

**`notion-token`** (headless):

```python
{
    "key": "notion-token",
    "label": "Notion (API token)",
    "description": "Notion MCP for automation without OAuth. Share each page with your integration.",
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@notionhq/notion-mcp-server"],
    "required_env": ["NOTION_TOKEN"],
    "capability_tags": ["notion", "productivity", "notes", "database", "automation", "headless"],
    "homepage": "https://www.notion.so/my-integrations",
    "auto_spawnable": False,
},
```

**`trello`**:

```python
{
    "key": "trello",
    "label": "Trello",
    "description": "Manage Trello boards, lists, and cards.",
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@delorenj/mcp-server-trello"],
    "required_env": ["TRELLO_API_KEY", "TRELLO_TOKEN"],
    "capability_tags": ["trello", "kanban", "boards", "cards", "productivity", "project-management"],
    "homepage": "https://github.com/delorenj/mcp-server-trello",
    "auto_spawnable": False,
},
```

Update module docstring to document optional `auth_type` field (`oauth` | absent).

### 2. `mcp_admin_routes.py`: honor `auth_type` on catalog add

In `add_mcp_from_catalog` (or equivalent handler):

- When entry has `auth_type: oauth`, set `server_config["auth"] = "oauth"` on save.
- When entry has `url` and no `command`, persist `url` only (HTTP transport).
- Do not put placeholder tokens in `env` for OAuth entries.

Expose `auth_type` in `GET /api/mcp/catalog` JSON (frontend type update in same prompt).

### 3. `optional-mcps/notion/manifest.yaml` (NEW)

Follow `linear/manifest.yaml`:

```yaml
manifest_version: 1
name: notion
description: Official Notion hosted MCP (OAuth). Read and write pages and databases.
source: https://developers.notion.com/guides/mcp/get-started-with-mcp

transport:
  type: http
  url: https://mcp.notion.com/mcp

auth:
  type: oauth

post_install: |
  Run `keprix mcp login notion` to complete OAuth in your browser.
  Start a new Keprix chat session so Notion tools load.
  For headless automation, use catalog key `notion-token` instead.
```

### 4. `optional-mcps/trello/manifest.yaml` (NEW)

Follow `n8n/manifest.yaml` api_key pattern:

```yaml
manifest_version: 1
name: trello
description: Trello boards, lists, and cards via community MCP server.
source: https://github.com/delorenj/mcp-server-trello

transport:
  type: stdio
  command: npx
  args: ["-y", "@delorenj/mcp-server-trello"]

auth:
  type: api_key
  env:
    - name: TRELLO_API_KEY
      prompt: "Trello API key (from trello.com/power-ups/admin)"
      required: true
      secret: false
    - name: TRELLO_TOKEN
      prompt: "Trello user token (generate from the same Power-Up admin page)"
      required: true
      secret: true

post_install: |
  Requires Node.js for npx. Start a new Keprix session after install.
```

### 5. Frontend: catalog types and credential hints

**`frontend/src/lib/admin-api.ts`**

- Add optional `auth_type?: "oauth" | null` to `McpCatalogEntry`.

**`frontend/src/app/(workspace)/admin/mcp/page.tsx`**

Extend `CREDENTIAL_HINTS`:

```typescript
NOTION_TOKEN: "Create at notion.so/my-integrations; share pages with the integration",
TRELLO_API_KEY: "Get from trello.com/power-ups/admin",
TRELLO_TOKEN: "Generate token from the same Power-Up admin page",
```

Catalog card behavior:

- `auth_type === "oauth"`: **Add** saves server; show info Alert "Run Connect after adding"
  (full Connect button ships in prompt 173; for this prompt, document in success message).
- `required_env` non-empty: existing credential dialog (unchanged).

Group or tag productivity entries with a `Productivity` chip if `capability_tags` contains
`productivity`.

### 6. Tests

**`src/keprix/tests/keprix_cli/test_autonomous_mcp_catalog.py`**

- Catalog length increases by 3 (17 total).
- `get_entry("notion")` has `auth_type == "oauth"` and `url`.
- `get_entry("trello")` has two `required_env` entries.
- `find_by_tags(["kanban"])` includes trello.

**`src/keprix/tests/keprix_cli/test_dashboard_admin_endpoints.py`** (or dedicated file)

- `POST /api/mcp/catalog/notion/add` saves `auth: oauth`, no command.
- `POST /api/mcp/catalog/trello/add` with env saves command/args/env.
- `POST /api/mcp/catalog/notion-token/add` requires `NOTION_TOKEN` in body.

**Manifest tests** (if pattern exists for linear/n8n; else add minimal parse test):

- Load `optional-mcps/notion/manifest.yaml` and `trello/manifest.yaml` via `mcp_catalog.py`.

---

## Acceptance criteria

1. `GET /api/mcp/catalog` returns `notion`, `notion-token`, and `trello` with correct fields.
2. Browse catalog tab shows all three with homepage links and credential requirements.
3. Adding `notion` writes `url` + `auth: oauth` to `config.yaml`.
4. Adding `trello` with credentials writes stdio config with redacted env on GET.
5. `keprix mcp install notion` and `keprix mcp install trello` complete without error
   (smoke test with mocked probe if live npx is unavailable in CI).
6. No regression on existing 14 catalog entries or auto-spawn tests.
7. TypeScript compiles on changed frontend files.

---

## What this prompt does NOT do

- OAuth Connect button and connection status chips (prompt 173).
- Vault-backed credential picker (prompt 173).
- Notion RAG connector (prompt 174).
- New `trello` skill (prompt 175).
- Operator documentation beyond inline homepage links (prompt 176).
