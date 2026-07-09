# Notion + Trello weekly sync (example playbook)

Demonstrates routing between **Trello MCP or skill** (list cards) and **Notion MCP or skill** (write summary). Use this as a template for productivity automations in Keprix.

## Prerequisites

1. **Trello**
   - Add the Trello MCP server from `/admin/mcp` (catalog → Trello), **or**
   - Set `TRELLO_API_KEY` and `TRELLO_TOKEN` in `.env` for the `trello` skill.
2. **Notion**
   - Add **Notion** (OAuth) or **Notion (API token)** from `/admin/mcp`, **or**
   - Set `NOTION_TOKEN` / `NOTION_API_KEY` for the `notion` skill.
3. Copy `board_id` and `notion_page_id` from Trello and Notion URLs.

## Variables

| Variable | Description |
| --- | --- |
| `board_id` | Trello board ID (24-char hex from the board URL) |
| `notion_page_id` | Notion page ID to append the weekly summary |

## Playbook file

See [`playbook.yaml`](playbook.yaml). Steps use agent prompts so you can run them from chat or wire them into a future playbook runner.

## Related docs

- MCP admin: `/admin/mcp`
- Notion RAG indexing (search, not live edit): `/rag-pipeline?source=notion`
- Routing skill: `productivity-integrations` in `/skills`
