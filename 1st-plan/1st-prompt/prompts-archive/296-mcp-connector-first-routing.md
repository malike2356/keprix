# Keprix - Prompt 296: MCP connector-first routing

**Pack:** Fable-class product power (292-297)  
**Master reference:** `../prompts-archive/ref-292-fable-class-product-power-master-reference.md`  
**Depends on:** **294** deferred tools; MCP discovery / admin; connector catalog

## UI entry point

Primary location: Integrations / MCP admin (existing)  
Secondary locations: Session suggest-connector chip; Settings > integrations  
Empty state: "No connectors yet. Add MCP servers or enable a catalog connector."  
Discovery trigger: when agent would otherwise browser-scrape a connected category  
Nav placement: Integrations / Admin > MCP

## Context

Fable prefers connected MCP apps over the browser. It searches a connector registry, suggests one-click connect, and only browses when no connector fits. That is product power: the agent uses the user's real tools instead of pretending via HTML.

Keprix already discovers MCP tools and has admin/CLI. This prompt adds **routing policy**: connector-first decisioning in the agent loop.

## What already exists (do not rebuild)

- `tools/mcp_tool.py`, MCP CLI (`keprix mcp`), admin routes
- Connector catalog / Google Workspace connector (archived packs)
- Browser / web_search / web_fetch tools
- Deferred tool bridge (**294**)

## What to build

### 1. Connector router

`src/keprix/agent/connector_router.py`:

```python
class ConnectorRouter:
    """
    Order:
      1. Connected MCP / integration tool that matches the category
      2. search_mcp_registry / catalog suggest_connectors
      3. Browser / web_fetch only if no connector fits
    """
```

Category examples: calendar, email, drive/docs, issues, chat, crm.

### 2. Tools

- `search_mcp_registry(query)`: find available but not connected servers
- `suggest_connectors(ids)`: UI prompt to connect (one click / deep link)
- Tag third-party MCP tools clearly in descriptions (`[third_party_mcp_app]` or Keprix equivalent)

### 3. Opt-in for third-party MCP

Do not silently call a newly suggested third-party connector. Flow:

1. search registry
2. suggest connect
3. after connected (or already connected + category match), call tool

Named connector that is already connected: call directly.

### 4. Prompt layer

```text
Check connected MCP / integrations before using the browser.
If a connector fits the category, use it.
If the user names a connector that is not connected, search then suggest connect.
Do not invent fake MCP UIs or simulated tool outputs.
```

### 5. Tests

- Calendar request with Google Calendar connected skips browser
- Unconnected Gmail request yields suggest_connectors, not scrape
- Deferred MCP tools still require tool_search (**294**)

## Files to create / modify

```
src/keprix/agent/connector_router.py
src/keprix/tools/mcp_registry_tools.py
src/keprix/agent/layers/tools.py
frontend: SuggestConnectorChip (minimal)
tests/agent/test_connector_router.py
docs/features/mcp-connector-first.md
```

## Acceptance criteria

- Connected category tools beat browser by default.
- Suggest-connect path works for catalogued but disconnected servers.
- No fake/simulated MCP outputs.
- Scout can log `connector.suggested` and `connector.used`.

## Contact

Verlox Ltd: [contact@verlox.uk](mailto:contact@verlox.uk)
