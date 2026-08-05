# keprix - Prompt 17: MCP, ACP, and External Integrations

## Context

Sources:
- `hermes-agent/acp_adapter/` - Agent Communication Protocol adapter
- `hermes-agent/acp_registry/` - ACP registry entry
- `openclaw/src/acp/` - OpenClaw ACP (TypeScript reference)
- `hermes-agent/mcp_serve.py` - MCP server entry point
- `hermes-agent/optional-mcps/` - optional MCP servers
- `odysseus/mcp_servers/` - Odysseus MCP servers
- `odysseus/routes/mcp_routes.py` - Odysseus MCP route management
- `core.carinaai.uk/src/mcp/` - Aiva (commercial) MCP
Output: `keprix/backend/mcp/`, `keprix/backend/acp/`

## MCP (Model Context Protocol)

keprix is both an MCP server (exposing its tools to other agents) and an MCP
client (consuming external MCP servers to extend its own tools).

### MCP Server (keprix exposes tools)

Port `hermes-agent/mcp_serve.py` to `backend/mcp/server.py`. This starts an MCP
server that exposes all 71+ CE tools to any MCP-compatible client.

Command: `python -m keprix mcp serve --port 3334`

All tools from Prompt 05 are exposed. Tool schema follows MCP spec.

Port `hermes-agent/agent/transports/carina_tools_mcp_server.py` (renamed from
`hermes_tools_mcp_server.py` in Prompt 03).

### MCP Client (keprix consumes external MCP servers)

Port from Odysseus:
```
mcp_servers/memory_server.py   -> backend/mcp/builtin/memory.py  (already Prompt 06)
mcp_servers/email_server.py    -> backend/mcp/builtin/email.py   (already Prompt 11)
mcp_servers/image_gen_server.py -> backend/mcp/builtin/image_gen.py
mcp_servers/rag_server.py      -> backend/mcp/builtin/rag.py     (already Prompt 06)
routes/mcp_routes.py           -> backend/mcp/client_routes.py
```

`backend/mcp/client.py` - MCP client manager:
```
POST   /api/mcp/servers               - add external MCP server
GET    /api/mcp/servers               - list configured MCP servers + status
DELETE /api/mcp/servers/{id}          - remove
POST   /api/mcp/servers/{id}/connect  - test connection + fetch tool list
GET    /api/mcp/tools                 - list all tools (built-in + from all MCP servers)
```

At startup, auto-connect to all configured MCP servers and merge their tools
into the tool dispatcher (Prompt 05). MCP server tools appear alongside built-in
tools with a `mcp:` prefix.

### Optional MCP Servers

Port from `hermes-agent/optional-mcps/`:
```
optional-mcps/linear/   -> backend/mcp/optional/linear/
optional-mcps/n8n/      -> backend/mcp/optional/n8n/
```

These are off by default. Users enable them in settings.

## ACP (Agent Communication Protocol)

Port from `hermes-agent/acp_adapter/` verbatim:
```
acp_adapter/auth.py          -> backend/acp/auth.py
acp_adapter/edit_approval.py -> backend/acp/edit_approval.py
acp_adapter/entry.py         -> backend/acp/entry.py
acp_adapter/events.py        -> backend/acp/events.py
acp_adapter/__init__.py      -> backend/acp/__init__.py
acp_adapter/__main__.py      -> backend/acp/__main__.py
acp_adapter/permissions.py   -> backend/acp/permissions.py
acp_adapter/provenance.py    -> backend/acp/provenance.py
acp_adapter/server.py        -> backend/acp/server.py
acp_adapter/session.py       -> backend/acp/session.py
acp_adapter/tools.py         -> backend/acp/tools.py
```

Port the ACP registry:
```
acp_registry/agent.json      -> backend/acp/registry/agent.json
acp_registry/icon.svg        -> backend/acp/registry/icon.svg
```

Update `backend/acp/registry/agent.json`:
- `"name": "keprix"`
- `"displayName": "keprix"`
- Remove any OpenClaw/Hermes identifiers

### ACP from OpenClaw

Read `openclaw/src/acp/` (TypeScript) to check for ACP features not present in
Hermes. Port any net-new ACP capabilities as Python equivalents to `backend/acp/`.

The ACP adapter enables keprix to:
- Act as an ACP server (receive tasks from ACP orchestrators)
- Act as an ACP client (delegate sub-tasks to other ACP agents)
- Support edit approval workflow (human-in-the-loop for file edits)

### IDE Hooks

From Aiva (commercial) `core.carinaai.uk/src/acp/` and Hermes ACP:
- VS Code extension hook: exposes keprix as an agent in VS Code via ACP
- JetBrains hook: same for JetBrains IDEs
- Codex plugin: `odysseus/integrations/codex/` + `openclaw/src/agents/` Codex integration

Port `odysseus/integrations/codex/` to `keprix/backend/integrations/codex/`:
```
integrations/codex/.codex-plugin/plugin.json -> backend/integrations/codex/plugin.json
integrations/codex/scripts/odysseus_api.py   -> backend/integrations/codex/carina_api.py
```
Update `carina_api.py`: replace all `odysseus` with `keprix`.

Port `odysseus/integrations/claude/README.md` -> `keprix/docs/integrations/claude.md`.

## Webhooks

From Odysseus `routes/webhook_routes.py`:
```
routes/webhook_routes.py -> backend/integrations/webhook_routes.py
```

```
POST   /api/webhooks                  - create webhook
GET    /api/webhooks                  - list
PUT    /api/webhooks/{id}             - update
DELETE /api/webhooks/{id}             - delete
POST   /api/webhooks/{id}/test        - send test payload

# Inbound webhooks (trigger agent from external systems):
POST   /api/webhooks/inbound/{token}  - receive inbound webhook, run agent
```

Inbound webhooks allow external systems (GitHub, Zapier, n8n) to trigger Carina
CE agent tasks. Security: validate webhook signature (HMAC-SHA256).
Port SSRF protection from tests: `odysseus/tests/test_webhook_ssrf_resilience.py`
Port auth tests: `odysseus/tests/test_webhook_trigger_auth_exempt.py`

```sql
CREATE TABLE webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,              -- outbound: where to POST
    events TEXT[] NOT NULL,         -- which events trigger this webhook
    secret TEXT,                    -- HMAC secret for inbound
    token TEXT UNIQUE,              -- inbound URL token
    is_active BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## API Token Management

From Odysseus `routes/api_token_routes.py`:
```
routes/api_token_routes.py -> backend/auth/api_token_routes.py
```

```
POST   /api/tokens                    - create API token (name, scopes)
GET    /api/tokens                    - list (masked)
DELETE /api/tokens/{id}               - revoke
POST   /api/tokens/validate           - validate token (used by mobile apps + MCP clients)
```

API tokens allow programmatic access to keprix without cookie-based auth.
Scopes: `chat:read`, `chat:write`, `memory:read`, `memory:write`,
`workspace:read`, `workspace:write`, `tools:execute`, `admin`.

## N8N Integration

`backend/mcp/optional/n8n/` provides a two-way n8n bridge:
- n8n can trigger keprix tasks via webhook
- keprix can trigger n8n workflows via its workflow API
- Configure: `N8N_BASE_URL`, `N8N_API_KEY`

## Linear Integration

`backend/mcp/optional/linear/` provides Linear issue management as MCP tools:
- `linear_create_issue`, `linear_list_issues`, `linear_update_issue`
- Configure: `LINEAR_API_KEY`

## Google Meet Integration

Port from `hermes-agent/plugins/google_meet/` to `backend/plugins/google_meet/`.
- Join meetings, transcribe, summarize
- Requires: `GOOGLE_MEET_OAUTH_CLIENT_ID`, `GOOGLE_MEET_OAUTH_CLIENT_SECRET`

## Spotify Integration

Port from `hermes-agent/plugins/spotify/` to `backend/plugins/spotify/`.
- Control playback, get now playing, search tracks
- Requires: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`

## Acceptance Criteria

- `python -m keprix mcp serve` starts MCP server on port 3334
- MCP `list_tools` returns at least 71 tools
- `POST /api/mcp/servers` with a valid MCP server URL adds it and fetches its tools
- `POST /api/webhooks/inbound/{token}` with a valid token triggers an agent response
- `POST /api/tokens` creates a token; `POST /api/tokens/validate` with that token returns 200
- ACP server responds to ACP session init protocol
- Codex plugin JSON is valid JSON at `backend/integrations/codex/plugin.json`
