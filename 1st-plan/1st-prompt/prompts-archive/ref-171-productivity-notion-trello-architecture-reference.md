# Keprix Prompt 171: Productivity Integrations (Notion + Trello) - Architecture Reference

**Status:** Reference document. Do not archive. Read before building prompts 172-176.

---

## What this prompt pack builds

Keprix can already connect to arbitrary MCP servers via `/admin/mcp` and `config.yaml`,
but **Notion and Trello are not first-class** today:

1. They are missing from the browse catalog (`autonomous_mcp_catalog.py`).
2. They are missing from the Nous-approved optional MCP manifests (`optional-mcps/`).
3. Notion hosted OAuth (`https://mcp.notion.com/mcp`) has no guided "Connect" flow in the UI.
4. Trello requires manual stdio setup with two env vars and no credential hints.
5. Notion RAG ingestion is documented in `docs/features/rag-pipelines.md` but has **no
   implemented connector** in `src/keprix/rag_pipeline/`.
6. The built-in `notion` skill exists but is not linked from MCP settings or onboarding.
7. There is no operator doc explaining **when to use MCP vs RAG vs skills** for the same app.

Prompts 172-176 deliver full use of **all three integration paths** for Notion and Trello:

| Path | Notion | Trello | Use when |
| --- | --- | --- | --- |
| **MCP (live)** | OAuth hosted + token stdio | Community stdio MCP | Create/update boards, pages, cards in chat |
| **RAG (search)** | Notion source connector | N/A (out of scope for RAG) | Agent searches indexed Notion corpus |
| **Skills (lightweight)** | `notion` skill (API/`ntn`) | New `trello` skill (REST via terminal) | One-off API calls without MCP install |

---

## Current state map (do not re-implement)

| File | What it does |
| --- | --- |
| `src/keprix/keprix_cli/autonomous_mcp_catalog.py` | 14-entry browse catalog for `/admin/mcp`. No Notion/Trello. |
| `src/keprix/keprix_cli/mcp_catalog.py` | Nous-approved manifests under `optional-mcps/`. Only `linear`, `n8n` today. |
| `src/keprix/keprix_cli/mcp_admin_routes.py` | Shared MCP admin API (servers, catalog, auto-spawn). Mounted on dashboard + main API. |
| `src/keprix/keprix_cli/mcp_spawn_settings.py` | Auto-spawn via env or `mcp.auto_spawn_enabled` in config. |
| `src/keprix/tools/mcp_tool.py` | MCP client; OAuth via `mcp_oauth_manager`, `keprix mcp login`. |
| `src/keprix/optional-mcps/linear/manifest.yaml` | Reference for OAuth remote MCP install. |
| `src/keprix/skills/productivity/notion/SKILL.md` | Notion API + `ntn` CLI skill. |
| `src/keprix/rag_pipeline/` | Pipeline runtime; file/text ingest only. No external source connectors yet. |
| `frontend/src/app/(workspace)/admin/mcp/page.tsx` | MCP admin UI with catalog tab and auto-spawn toggle. |
| `frontend/src/lib/ce-api.ts` | `mcpApi()` + `NEXT_PUBLIC_MCP_API_URL` for configurable MCP API base. |
| `docs/features/rag-pipelines.md` | Documents Notion source; implementation gap. |

### Autonomous MCP pack (158-161) already shipped

Do not rebuild catalog UI, auto-spawn tool, or management UI. **Extend** them with Notion/Trello
entries and connection UX only.

---

## Catalog entries to add (prompt 172)

### Notion (hosted OAuth, recommended)

```yaml
key: notion
label: Notion
description: Read and write Notion pages and databases via official hosted MCP.
transport: http
url: https://mcp.notion.com/mcp
required_env: []
auth_type: oauth          # new optional catalog field; see prompt 172
capability_tags: [notion, productivity, notes, database, wiki, pages]
auto_spawnable: false
homepage: https://developers.notion.com/guides/mcp/get-started-with-mcp
```

### Notion (token, headless)

```yaml
key: notion-token
label: Notion (API token)
description: Notion MCP for automation without interactive OAuth. Share pages with the integration.
transport: stdio
command: npx
args: ["-y", "@notionhq/notion-mcp-server"]
required_env: [NOTION_TOKEN]
capability_tags: [notion, productivity, notes, database, automation, headless]
auto_spawnable: false
```

### Trello

```yaml
key: trello
label: Trello
description: Manage Trello boards, lists, and cards.
transport: stdio
command: npx
args: ["-y", "@delorenj/mcp-server-trello"]
required_env: [TRELLO_API_KEY, TRELLO_TOKEN]
capability_tags: [trello, kanban, boards, cards, productivity, project-management]
auto_spawnable: false
homepage: https://github.com/delorenj/mcp-server-trello
```

**Auto-spawn:** All three entries set `auto_spawnable: false` (credentials or OAuth required).

---

## Optional MCP manifests (prompt 172)

Add `optional-mcps/notion/manifest.yaml` and `optional-mcps/trello/manifest.yaml` so
`keprix mcp install notion` and `keprix mcp install trello` work from CLI with install-time
tool checklist. Follow `linear/manifest.yaml` (OAuth HTTP) and `n8n/manifest.yaml` (api_key env)
patterns.

---

## Connection UX (prompt 173)

| Server type | After catalog add | User action |
| --- | --- | --- |
| `notion` (OAuth) | Saved with `auth: oauth` | Click **Connect** in UI or run `keprix mcp login notion`; browser OAuth |
| `notion-token` | Credential dialog | `NOTION_TOKEN` from notion.so/my-integrations; store in Vault optional |
| `trello` | Credential dialog | API key + token from trello.com/power-ups/admin |

UI additions on `/admin/mcp`:

- **Connection status** chip: `Connected`, `Needs OAuth`, `Needs credentials`, `Error`
- **Connect** button for OAuth servers (calls new API or documents CLI until API ships)
- **Open setup guide** link per catalog entry (`homepage` or inline help URL)
- Vault picker: "Use secret from Vault" for env vars when adding from catalog

Backend:

- `POST /api/mcp/catalog/{key}/add` must set `auth: oauth` when catalog entry has `auth_type: oauth`
- `GET /api/mcp/servers` should expose `auth` and `oauth_connected` (boolean from token storage)
- `POST /api/mcp/servers/{name}/oauth/start` (optional): return OAuth URL for in-app flow

---

## RAG path (prompt 174)

Notion-only. Implement `NotionSourceConnector` under `src/keprix/rag_pipeline/connectors/`.

- Reads `NOTION_TOKEN` or `KEPRIX_NOTION_TOKEN` from env/Vault
- Lists pages/databases shared with integration
- Fetches page markdown via Notion API (`Notion-Version: 2025-09-03`)
- Feeds chunks into existing `RagPipeline.ingest` path

UI: extend `PipelineBuilder` with source type `notion` and page/database picker (or ID list).

Link from `/admin/mcp` Notion card: "Index for search" opens `/rag-pipeline?source=notion`.

Trello has **no RAG connector** in this pack (boards change often; MCP is the right path).

---

## Skills path (prompt 175)

| Skill | Status | Action |
| --- | --- | --- |
| `notion` | Exists | Enable by default on productivity profile; link from MCP page |
| `trello` | Missing | New skill: REST via `terminal` + curl (mirror `airtable` skill pattern) |

Add `productivity-routing` skill or system fragment telling the agent:

1. Prefer **MCP tools** (`mcp_notion_*`, `mcp_trello_*`) when servers are connected.
2. Use **RAG query** when user asks to search indexed Notion content.
3. Fall back to **skills** when MCP is not configured.

Optional playbook template: `examples/productivity/notion-trello-sync/playbook.yaml`.

---

## Documentation and verification (prompt 176)

- `docs/integrations/productivity-notion-trello.md` (operator guide)
- Update `docs/integrations/mcp.md`, `docs/features/settings.md`, `frontend/.env.example`
- Golden eval: `evals/suites/productivity/notion-trello.yaml` (mocked HTTP)
- Agent brief: `prompts-archive/176-productivity-notion-trello-verification.md`

---

## Build order

| Prompt | Title | What it adds |
| --- | --- | --- |
| 172 | Catalog + manifests | Notion/Trello in browse catalog + `keprix mcp install` |
| 173 | Connection OAuth + Vault UX | Connect button, status chips, vault-backed credentials |
| 174 | Notion RAG connector | Source connector + pipeline UI + cross-link from MCP |
| 175 | Skills + agent routing | `trello` skill, routing rules, playbook example |
| 176 | Docs + E2E verification | Operator guide, evals, agent brief |

Build **172 first** (data layer). **173** depends on 172. **174** and **175** can parallelize after 172.
**176** last.

---

## Safety constraints (all prompts)

1. Never log or return raw `NOTION_TOKEN`, `TRELLO_TOKEN`, or OAuth refresh tokens in API responses.
2. Run `validate_mcp_server_entry` on every catalog add (existing path via `_save_mcp_server`).
3. Trello and Notion MCPs are **never** auto-spawnable (`auto_spawnable: false`).
4. OAuth servers must not store fake bearer tokens in `env`; use `auth: oauth` only.
5. RAG connector is **read-only**; no write path to Notion from RAG ingest.
6. Document that Notion OAuth is unsuitable for unattended cron; point operators to `notion-token`.

---

## Acceptance gate for the full pack (after 172-176)

1. Add **Notion** from browse catalog; complete OAuth; new chat lists `mcp_notion_*` tools.
2. Add **Trello** from browse catalog with API key + token; list boards via agent.
3. Create a Notion RAG pipeline; ingest one database; agent answers from indexed content.
4. With MCP disconnected, agent uses `notion` / `trello` skills via terminal for a simple read.
5. `/admin/mcp` shows connection status and links to setup docs.
6. `keprix mcp install notion` and `keprix mcp install trello` succeed from CLI.
7. All new tests pass; no stub endpoints in production paths.
