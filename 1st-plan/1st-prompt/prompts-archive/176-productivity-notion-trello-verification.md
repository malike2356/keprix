# Agent brief: Productivity Notion/Trello verification (Prompt 176)

## Status: VERIFIED (2026-07-12)

Automated smoke closed this brief (18 passed, 2 skipped). Live Notion/Trello OAuth remains an optional operator check; it is not a pending build item.

## Goal

Verify MCP, RAG, and skills fallback paths after prompts 172-176.

## Automated smoke (archive gate)

```bash
cd /opt/lampp/htdocs/verlox/keprix
PYTHONPATH=src python3.11 -m pytest tests/evals/test_productivity_integrations.py -q
PYTHONPATH=src python3.11 -m pytest tests/integrations/test_productivity_notion_trello_pack.py -q
PYTHONPATH=src python3.11 -m pytest tests/skills/test_productivity_integrations_skills.py -q
```

**Result (2026-07-12):** 18 passed, 2 skipped.

## Optional live runbook

### MCP (live)

- Open `/admin/mcp` → **Browse catalog** → add **Notion** (`notion`).
- Click **Connect**; complete OAuth; status shows **Connected**.
- **List tools** returns `mcp_notion_*` tools.
- New chat: ask to search or update a shared Notion page; agent uses MCP tools.

### Trello MCP

- Set `TRELLO_API_KEY` and `TRELLO_TOKEN` in `.env` or Vault.
- Add **Trello** from catalog; server shows **Connected** or credentials accepted.
- Chat: "List my Trello boards" returns board names.

### RAG

- Set `KEPRIX_NOTION_TOKEN`; share at least one page with the integration.
- Open `/rag-pipeline?source=notion`; ingest one page; success message shown.
- `POST /api/rag-pipeline/query` with `source_types: ["notion"]` returns citations.
- From `/admin/mcp`, **Index for search** link opens RAG builder with Notion selected.

### Skills fallback

- Disable or remove Trello MCP server.
- Confirm `trello` skill is enabled in `/skills`.
- With env vars set, ask agent to list boards; verify `terminal` + curl path works.

### Vault

- Store `TRELLO_TOKEN` in `/vault`.
- Catalog add for Trello maps Vault key; server starts without plain token in config UI.

### Docs

- `bash scripts/serve-docs.sh` (or CI docs build); open **Integrations → Notion and Trello**.
- Links from `mcp.md` and `rag-pipelines.md` resolve.

## Pass criteria

- Automated tests green without live OAuth.
- No `coming soon` or TODO stubs in 172-175 production modules for Notion/Trello.
