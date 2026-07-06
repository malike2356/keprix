---
name: productivity-integrations
description: Route Notion and Trello work across MCP, RAG search, and curl skills.
version: 1.0.0
author: keprix
license: MIT
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [Notion, Trello, Productivity, MCP, RAG, Routing]
    related_skills: [notion, trello]
---

# Productivity integrations (Notion + Trello)

Keprix supports three integration paths for Notion and Trello. Pick the path that matches latency, credentials, and whether the user needs live edits or search over indexed content.

## Decision tree

### User wants live edit of Notion or Trello (create/update/move in chat)

1. **If MCP is connected**, use MCP tools (preferred):
   - Notion OAuth server (`notion`): tools prefixed `mcp_notion_*`
   - Notion token server (`notion-token`): tools prefixed `mcp_notion_token_*`
   - Trello stdio server (`trello`): tools prefixed `mcp_trello_*`
2. **Else if env credentials exist** (`NOTION_TOKEN`, `TRELLO_API_KEY` + `TRELLO_TOKEN`):
   - Suggest adding the server at `/admin/mcp` (catalog tab), **or**
   - Use the **`notion`** or **`trello`** skill with the `terminal` tool and `curl` / `ntn`.
3. **Else** guide the user to `/admin/mcp` (OAuth for Notion) or Power-Up admin for Trello keys.

### User wants search across Notion docs already indexed

Use the **RAG pipeline**, not live Notion MCP on every question:

1. **Ingest** (operator or cron): `POST /api/rag-pipeline/ingest/notion` with `pipeline_id`, optional `page_ids` / `database_ids`, and token from `KEPRIX_NOTION_TOKEN` or Vault. UI: `/rag-pipeline?source=notion` (**Ingest from Notion**).
2. **Query** indexed content: `POST /api/rag-pipeline/query` with:
   - `question`: natural language question
   - `pipeline_id`: target pipeline (e.g. `production-default`)
   - `source_types`: `["notion"]` to restrict hits to Notion-ingested chunks
   - `hybrid`: `true` (default) for hybrid retrieval when enabled
3. **Workspace UI:** `/rag-pipeline` for manual ingest, query, runs, and evaluations.

Trello has **no RAG connector**; use MCP or the `trello` skill for board data.

### User wants one-off read without MCP installed

- **Notion:** load the **`notion`** skill; prefer `ntn api v1/pages/{id}/markdown` on macOS/Linux, else `curl` with `Notion-Version: 2025-09-03`.
- **Trello:** load the **`trello`** skill; `GET /boards/{id}/cards?filter=open` via `curl`.

### User wants automation without OAuth browser

- **MCP:** add **`notion-token`** from the catalog (`NOTION_TOKEN` / Vault).
- **RAG:** set `KEPRIX_NOTION_TOKEN` and run ingest via API or `/rag-pipeline?source=notion`.
- **Skills:** `NOTION_API_KEY` or `NOTION_TOKEN` in `.env` for curl/`ntn` (see `notion` skill).

## MCP tool name prefixes

| Server name in config | Tool prefix | Transport |
| --- | --- | --- |
| `notion` | `mcp_notion_*` | HTTP OAuth (`https://mcp.notion.com/mcp`) |
| `notion-token` | `mcp_notion_token_*` | stdio (`@notionhq/notion-mcp-server`) |
| `trello` | `mcp_trello_*` | stdio (`@delorenj/mcp-server-trello`) |

List tools after connect: `/admin/mcp` **List tools**, or `keprix mcp tools trello`.

## Operator surfaces

| Goal | Where |
| --- | --- |
| Add MCP servers | `/admin/mcp` or Settings → MCP servers |
| Index Notion for search | `/rag-pipeline?source=notion` |
| Enable/disable skills | `/skills` |
| Example multi-step workflow | `examples/productivity/notion-trello-sync/` |

## Related skills

- **`notion`**: Notion API + `ntn` CLI (pages, databases, markdown).
- **`trello`**: Trello REST via `curl` (boards, lists, cards).

Load this skill when the user mentions Notion or Trello but has not specified MCP vs search vs a one-off API call.
