# K01: Keprix Agent Contract for Aiva

**Status: COMPLETED 2026-08-07**
**Phase:** 1 (Foundation)
**Priority:** P0 -- Build FIRST before anything else
**Depends on:** Nothing
**Target time:** 8 hours
**Location:** Keprix

## What was built

- `src/keprix/api/carina_agent_routes.py`: `POST /carina/agent/run` with `CARINA_KEPRIX_SHARED_TOKEN` bearer auth
- `src/keprix/agent/carina_bridge.py`: Carina message/tool contract adapted to Keprix LLM loop
- Workspace-isolated session store (`workspace_id::session_id`)
- Tool routing: Keprix native registry first, then Carina HTTP tools; unregistered tools return 400 with tool name
- Provider failover via `ProviderPool` (+ optional `CARINA_KEPRIX_FALLBACK_MODELS`)
- Max 10 iterations, 30s timeout per call
- Wired into `api/server.py`; env documented in `.env.example`
- Tests: `tests/api/test_carina_agent_routes.py` (9 passed)

## What This Builds

The `POST /carina/agent/run` endpoint on Keprix. This is the contract between Carina PHP and Keprix. Aiva sends conversation history, tools, and workspace context. Keprix runs the agent loop and returns the response.


## Contract

### Request

```
POST /carina/agent/run
Authorization: Bearer <CARINA_KEPRIX_SHARED_TOKEN>
Content-Type: application/json

{
  "workspace_id": "ws_abc123",
  "session_id": "sess_xyz789",
  "model": "deepseek-v4-pro",
  "temperature": 0.7,
  "system_prompt": "<worker persona + knowledge base + rules>",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "Find me property investors in Portsmouth"},
    {"role": "assistant", "content": null, "tool_calls": [...]},
    {"role": "tool", "tool_call_id": "...", "content": "<tool output>"}
  ],
  "tools": [
    {
      "name": "search_contacts",
      "description": "Search CRM contacts by criteria",
      "parameters": { "type": "object", "properties": {...} }
    }
  ],
  "carina_tools": [
    {
      "name": "search_contacts",
      "http_endpoint": "http://carina:80/api/carina/tools/search_contacts",
      "auth_header": "Bearer <shared_token>"
    }
  ]
}
```

### Response

```json
{
  "message": {
    "role": "assistant",
    "content": "I found 12 property investors..."
  },
  "tool_calls": [],
  "finish_reason": "stop",
  "session_id": "sess_xyz789",
  "usage": {
    "prompt_tokens": 450,
    "completion_tokens": 120,
    "total_tokens": 570
  }
}
```

### Tool Call Response (when agent wants to use a tool)

```json
{
  "message": {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_001",
        "type": "function",
        "function": {
          "name": "search_contacts",
          "arguments": "{\"query\": \"property investor Portsmouth\"}"
        }
      }
    ]
  },
  "tool_calls": [...],
  "finish_reason": "tool_calls",
  "session_id": "sess_xyz789",
  "usage": {...}
}
```

## Implementation

### File: `src/keprix/api/carina_agent_routes.py`

```python
"""Carina agent bridge -- POST /carina/agent/run"""

from fastapi import APIRouter, Request, HTTPException
from keprix.agent.carina_bridge import CarinaAgentBridge

router = APIRouter(prefix="/carina")
bridge = CarinaAgentBridge()

@router.post("/agent/run")
async def agent_run(request: Request):
    """Execute an agent turn for a Carina/Aiva workspace."""
    # Auth check
    auth = request.headers.get("Authorization", "")
    expected = f"Bearer {CARINA_KEPRIX_SHARED_TOKEN}"
    if auth != expected:
        raise HTTPException(status_code=401)

    body = await request.json()
    
    # Run Keprix agent loop
    result = await bridge.run(
        workspace_id=body["workspace_id"],
        session_id=body.get("session_id"),
        model=body.get("model", "deepseek-v4-pro"),
        temperature=body.get("temperature", 0.7),
        system_prompt=body["system_prompt"],
        messages=body["messages"],
        tools=body.get("tools", []),
        carina_tools=body.get("carina_tools", []),
    )
    
    return result
```

### File: `src/keprix/agent/carina_bridge.py`

The bridge adapts Carina's message format to Keprix's internal agent loop:

```python
class CarinaAgentBridge:
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.provider_pool = ProviderPool()
    
    async def run(self, workspace_id, session_id, model, temperature,
                  system_prompt, messages, tools, carina_tools):
        """Execute one agent turn."""
        # 1. Register Carina tools as callable Keprix tools
        for tool_def in carina_tools:
            self.tool_registry.register_http_tool(
                name=tool_def["name"],
                endpoint=tool_def["http_endpoint"],
                auth_header=tool_def.get("auth_header", ""),
                schema=tool_def.get("parameters", {}),
            )
        
        # 2. Build prompt with workspace isolation
        # 3. Call LLM via provider pool
        # 4. If tool_calls: execute tools (Keprix native or Carina HTTP)
        # 5. Return result in Carina contract format
```

### Key design decisions:

- **Session isolation:** Each workspace_id gets its own session namespace. Workspaces cannot see each other's memory.
- **Tool routing:** If a tool exists in Keprix's native registry, use it. If it's a `carina_tool`, call the HTTP endpoint. If neither, return error.
- **Max iterations:** 10 turns per `/agent/run` call. Prevents infinite loops.
- **Timeout:** 30 seconds per call. If exceeded, return partial result with error.

## Acceptance Criteria

- [x] POST /carina/agent/run with valid auth returns agent response
- [x] Invalid auth returns 401
- [x] Tool calls route correctly (Keprix native vs Carina HTTP)
- [x] Session state persists across multiple calls with same session_id
- [x] Workspace isolation: ws_a cannot access ws_b session data
- [x] Carina tools not registered: returns error with tool name
- [x] Provider failover works (if primary LLM fails, fallback)
