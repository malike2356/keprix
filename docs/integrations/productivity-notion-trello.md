# Notion and Trello productivity integrations

Keprix connects to **Notion** and **Trello** through three complementary paths. Pick the path that matches your goal: live edits in chat, search over indexed Notion content, or lightweight API calls without installing MCP.

## Overview: three paths

| Path | Notion | Trello | Best for |
| --- | --- | --- | --- |
| **MCP (live)** | OAuth hosted MCP or token stdio server | Community stdio MCP | Create, update, and query pages/cards during chat |
| **RAG (search)** | Notion source connector | Not supported | Agent searches a pre-indexed Notion corpus |
| **Skills (lightweight)** | `notion` skill (`ntn` or curl) | `trello` skill (curl) | One-off API calls when MCP is not installed |

Routing guidance for the agent lives in the **`productivity-integrations`** skill. Operator UI entry points:

| Surface | Route |
| --- | --- |
| MCP admin | `/admin/mcp` |
| RAG pipeline builder | `/rag-pipeline` (Notion: `?source=notion`) |
| Skills hub | `/skills` |
| Vault | `/vault` |
| Settings hub | `/settings` |

Related docs: [MCP](mcp.md), [RAG pipelines](../features/rag-pipelines.md), [Skills](../features/skills.md), [Vault](../security/vault.md).

---

## Quick start: Notion live (MCP OAuth)

Recommended for interactive chat where the agent reads and writes Notion pages and databases.

1. Open **Settings** → **MCP servers** (`/admin/mcp`).
2. Open the **Browse catalog** tab.
3. Find **Notion** and click **Add**.
4. On **My servers**, click **Connect** next to the `notion` server (or run `keprix mcp login notion` from the CLI).
5. Complete OAuth in the browser; return to the MCP page and confirm status **Connected**.
6. Click **List tools** to verify `mcp_notion_*` tools are available.
7. Start a new chat and try:
   - "Search my Notion workspace for pages about onboarding."
   - "Create a new page titled Weekly standup under page `{parent_page_id}`."

**Catalog key:** `notion`  
**Transport:** HTTP → `https://mcp.notion.com/mcp`  
**Auto-spawn:** off (credentials/OAuth required before use).

---

## Quick start: Notion headless (API token)

For automation, CI, or servers without a browser for OAuth.

1. Create an integration at [notion.so/my-integrations](https://www.notion.so/my-integrations).
2. Copy the integration token (`secret_...` or `ntn_...`).
3. In Notion, open each target page or database → **...** → **Connect to** → your integration name.  
   Without this step the API returns **404** even when the page exists.
4. At `/admin/mcp` → **Browse catalog** → add **Notion (API token)** (`notion-token`).
5. Enter `NOTION_TOKEN` in the credential dialog, or pick a Vault key (see [Vault](#vault)).
6. Enable the server and **List tools** (`mcp_notion_token_*` prefix).

Alternative without MCP: set `NOTION_TOKEN` or `NOTION_API_KEY` in `.env` and use the **`notion`** skill via the `terminal` tool.

---

## Quick start: Trello

1. Open [trello.com/power-ups/admin](https://trello.com/power-ups/admin).
2. Create or open a Power-Up and copy the **API key**.
3. Generate a **token** with the scopes you need (read/write boards and cards).
4. Add to `${KEPRIX_HOME:-~/.keprix}/.env`:
   ```bash
   TRELLO_API_KEY=your_key
   TRELLO_TOKEN=your_token
   ```
5. At `/admin/mcp` → **Browse catalog** → add **Trello** (`trello`).
6. Confirm credentials (or map Vault keys on catalog add).
7. **List tools** and verify `mcp_trello_*` tools.
8. In chat: "List my Trello boards" or "Show open cards on board `{board_id}`."

**Catalog key:** `trello`  
**Package:** `@delorenj/mcp-server-trello` (stdio via `npx`).

---

## Search Notion with RAG

Use RAG when the agent should **search indexed Notion content** without calling live Notion MCP on every question. Trello is not indexed by RAG; use MCP or the `trello` skill instead.

### 1. Set a token

```bash
KEPRIX_NOTION_TOKEN=secret_your_integration_token
```

Same integration token as headless Notion; share pages with the integration first.

### 2. Index content

**UI:** open [`/rag-pipeline?source=notion`](../features/rag-pipelines.md). Select **Notion** as source type, set pipeline ID and store kind, optionally paste page or database IDs, then **Ingest from Notion**.

**API:**

```bash
curl -s -X POST http://127.0.0.1:3333/api/rag-pipeline/ingest/notion \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_id": "production-default",
    "page_ids": ["your-page-id"],
    "store_kind": "memory"
  }'
```

From `/admin/mcp`, connected Notion servers show **Index for search** linking to the RAG builder.

### 3. Query indexed content

```bash
curl -s -X POST http://127.0.0.1:3333/api/rag-pipeline/query \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_id": "production-default",
    "question": "What does the handbook say about HVAC maintenance?",
    "source_types": ["notion"]
  }'
```

See [RAG pipelines](../features/rag-pipelines.md#notion-source-connector) for connector details and `GET /api/rag-pipeline/connectors`.

---

## Skills fallback

When MCP is not configured, load bundled skills:

| Skill | Purpose |
| --- | --- |
| `notion` | Notion API via `ntn` CLI or curl |
| `trello` | Trello REST via curl |
| `productivity-integrations` | Decision tree: MCP vs RAG vs skills |

List installed skills:

```bash
keprix skills list
```

Toggle skills globally or per platform:

```bash
keprix skills config
```

Bundled productivity skills are **enabled by default**. Opt out in `~/.keprix/config.yaml`:

```yaml
skills:
  disabled:
    - trello
```

The MCP admin page **Also available without MCP** box links to `/skills` and `/rag-pipeline?source=notion`.

---

## Vault

Store integration tokens encrypted instead of plain `.env` values.

1. Open `/vault` and save secrets (e.g. `notion_api_token`, `TRELLO_TOKEN`).
2. When adding **Trello** or **notion-token** from the catalog, map env var names to Vault keys in the credential dialog.
3. RAG ingest resolves `KEPRIX_NOTION_TOKEN`, `NOTION_TOKEN`, or Vault-backed values when configured.

See [Vault](../security/vault.md) for backup and key rotation.

---

## Auto-spawn

Notion and Trello catalog entries set **`auto_spawnable: false`**. The agent will not spawn these servers automatically during tasks; you must add them from `/admin/mcp` and supply OAuth or API credentials first.

The **Auto-spawn** toggle on `/admin/mcp` controls the global catalog auto-spawn feature (`KEPRIX_AUTO_MCP_SPAWN`). It does not bypass per-entry `auto_spawnable: false` for Notion/Trello.

---

## Environment variables

| Variable | Used by |
| --- | --- |
| `KEPRIX_NOTION_TOKEN` | RAG Notion ingest (`/api/rag-pipeline/ingest/notion`) |
| `NOTION_TOKEN` | `notion-token` MCP, `notion` skill |
| `NOTION_API_KEY` | `notion` skill (alias for integration token) |
| `TRELLO_API_KEY` | Trello MCP, `trello` skill |
| `TRELLO_TOKEN` | Trello MCP, `trello` skill |
| `NEXT_PUBLIC_MCP_API_URL` | Frontend MCP admin API base (defaults to main API URL) |
| `KEPRIX_AUTO_MCP_SPAWN` | Agent auto-spawn for spawnable catalog entries only |
| `KEPRIX_MCP_ALLOWED_SERVERS` | Optional allow list for MCP server names |

Frontend: see `frontend/.env.example` for `NEXT_PUBLIC_MCP_API_URL` when the dashboard runs on a different port than the main API.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Notion OAuth **Connect** fails or loops | Callback URL or session mismatch | Retry `keprix mcp login notion`; confirm API reachable at `NEXT_PUBLIC_API_URL` |
| Notion API **404** on a known page | Integration not connected to page | In Notion UI: page menu → **Connect to** → your integration |
| Notion RAG ingest finds **no pages** | Empty workspace search or wrong IDs | Pass explicit `page_ids` / `database_ids`; confirm `KEPRIX_NOTION_TOKEN` |
| Trello **401** | Invalid key/token pair | Regenerate token at Power-Up admin; update `.env` or Vault |
| Trello MCP **needs_credentials** | Env vars missing at server start | Set `TRELLO_API_KEY` and `TRELLO_TOKEN`; restart gateway or re-add from catalog |
| MCP admin empty / wrong catalog | Frontend pointing at wrong API port | Set `NEXT_PUBLIC_MCP_API_URL` to main API (e.g. `http://localhost:3333`) |
| `mcp_notion_*` tools missing | Server disabled or OAuth not finished | Enable server; complete **Connect**; run **List tools** |
| Agent uses curl instead of MCP | MCP not connected or skill loaded first | Add MCP server; load `productivity-integrations` skill for routing |

---

## Example playbook

Multi-step Trello → Notion summary workflow:

```text
examples/productivity/notion-trello-sync/
```

See `playbook.yaml` and `README.md` in that directory.

---

## Verification

Automated smoke: `tests/evals/test_productivity_integrations.py` and `tests/integrations/test_productivity_notion_trello_pack.py`.

Eval suite: `evals/suites/productivity/notion-trello.yaml`.
