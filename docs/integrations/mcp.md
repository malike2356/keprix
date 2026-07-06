# MCP integration

Model Context Protocol servers extend tools available to the agent.

## Workspace admin UI

Configure MCP servers from **`/admin/mcp`** (Settings → MCP servers). The page includes:

- **My servers** and **Browse catalog** tabs
- OAuth **Connect** for hosted servers (e.g. Notion)
- Credential and Vault mapping for stdio servers (e.g. Trello, `notion-token`)
- **Auto-spawn** toggle (global; per-catalog entries may still require manual credentials)
- **Also available without MCP** links to skills and Notion RAG indexing

CLI equivalent: `keprix mcp` (see [CLI reference](../reference/cli.md)).

## Productivity: Notion and Trello

First-class catalog entries:

| Catalog key | Label | Transport |
| --- | --- | --- |
| `notion` | Notion | HTTP OAuth (`https://mcp.notion.com/mcp`) |
| `notion-token` | Notion (API token) | stdio (`@notionhq/notion-mcp-server`) |
| `trello` | Trello | stdio (`@delorenj/mcp-server-trello`) |

Tool prefixes after connect: `mcp_notion_*`, `mcp_notion_token_*`, `mcp_trello_*`.

Full operator guide (MCP, RAG, skills, Vault, troubleshooting): **[Notion and Trello productivity integrations](productivity-notion-trello.md)**.

## Allow list

```bash
KEPRIX_MCP_ALLOWED_SERVERS=
```

Only listed servers may be started by the runtime when this variable is set.

## Developer UI

Legacy MCP configuration may also appear under `/developer` depending on your deployment. Prefer `/admin/mcp` for catalog add, OAuth, and connection status.

## Related

- [Notion and Trello productivity integrations](productivity-notion-trello.md)
- [RAG pipelines](../features/rag-pipelines.md)
- [Skills](../features/skills.md)
- [Vault](../security/vault.md)
