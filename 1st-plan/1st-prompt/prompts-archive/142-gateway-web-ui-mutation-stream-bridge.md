# Keprix - Prompt 142: Gateway Web UI NDJSON Stream Bridge

## Context

Read `138-chat-mutation-e2e-wiring-outline.md`.

Complete Prompts **139-141** first. Those prove mutation E2E via a chat-sidecar
bridge. This prompt unifies `/chat` with the same agent runtime used by
Telegram, Discord, and slash commands so mutation is not a special case.

Depends on Prompt **71** (interface registry) and Prompt **23** (gateway dispatch).

Output: `src/keprix/interfaces/`, `src/keprix/gateway/`,
`src/keprix/api/conversation_routes.py`, `tests/interfaces/test_web_ui_stream.py`.

## Problem

`_stream_assistant_reply` uses two disconnected paths:

1. Slash commands -> `registry.dispatch(InterfaceKind.WEB_UI, ...)`
2. Everything else -> `stream_chat_completion` (no tools, no mutation)

Telegram/Discord handlers can run tool loops; web chat cannot. Prompt 139 patched
mutation in via `chat_mutation_bridge`; this prompt replaces that split with one
streaming gateway path.

## Architecture

```
_stream_assistant_reply
  -> registry.dispatch(
       agent_id="default",
       kind=InterfaceKind.WEB_UI,
       message=user_text,
       user_id=...,
       session_id=...,
       stream=True,
     )
  -> AsyncIterator[GatewayStreamEvent]
  -> map to NDJSON (text_delta, tool_call, mutation, text_done)
```

Keep `maybe_run_mutation_for_chat` as fallback only when gateway reports
`tool_not_found` until Prompt 143 moves mutation inside the loop.

## Step 1: Gateway stream protocol

Define typed events in `src/keprix/gateway/stream_events.py`:

```python
@dataclass
class GatewayStreamEvent:
    event: Literal[
        "text_delta", "text_done", "tool_call", "tool_call_update",
        "mutation", "error", "done",
    ]
    payload: dict[str, Any]
```

Document the contract in `docs/features/agent.md` (short section only).

## Step 2: WEB_UI handler streaming

File: `src/keprix/interfaces/interface_registry.py` (or dedicated
`web_ui_handler.py`)

Extend `_web_ui_handler` to accept `stream: bool = False`:

- When `stream=False`, preserve current dict return (backward compatible)
- When `stream=True`, return `AsyncIterator[GatewayStreamEvent]`

Implementation:

1. Run the same agent entry used by other channels (gateway runner /
   `conversation_loop` if present)
2. Yield `text_delta` as tokens arrive
3. Yield `tool_call` / `tool_call_update` when tools execute
4. Yield `mutation` when mutation engine produces a pending record (delegate to
   engine; do not duplicate synthesis logic)
5. Yield `text_done` and `done` at end

## Step 3: Map gateway events in conversation API

In `conversation_routes.py`:

```python
async def _stream_assistant_reply(...):
    if user_text.strip().startswith("/"):
        ...  # existing slash path OR fold into dispatch with slash parser
    async for gw_event in registry.dispatch_stream(...):
        yield _map_gateway_event(gw_event)
```

`_map_gateway_event` must produce the exact shapes `useChat.ts` already parses
(see Prompt 136 block types).

## Step 4: Feature flag for rollout

Add `KEPRIX_CHAT_GATEWAY_STREAM=true` in `.env.example`.

- When true: use gateway stream path for all non-empty messages
- When false: keep Prompt 139 bridge + `stream_chat_completion` fallback

Default `true` in dev; document in `docs/configuration/environment-variables.md`.

## Step 5: Deprecate duplicate mutation entry (partial)

When gateway stream is enabled and emits `mutation` events:

- Do **not** also run `maybe_run_mutation_for_chat` on the same turn (double
  synthesis bug)
- Log at debug when bridge is skipped

Full removal of the bridge waits for Prompt 143.

## Step 6: Tests

`tests/interfaces/test_web_ui_stream.py`:

1. Mock gateway runner to emit text + tool_call sequence
2. Assert NDJSON mapping via `_stream_assistant_reply` helper or TestClient
3. Mock mutation event in stream; assert `event: mutation` shape
4. Flag off: assert fallback to chat_completion mock (no gateway call)

`tests/api/test_conversation_routing.py` (extend if exists):

- Slash `/tools` still works
- Gateway stream flag on routes message through dispatch mock

## Acceptance Criteria

- `/chat` with `KEPRIX_CHAT_GATEWAY_STREAM=true` uses gateway dispatch, not raw
  `stream_chat_completion`
- Tool calls appear as `tool_call` blocks in the feed (Prompt 136 AC)
- Mutation events can originate from gateway stream without double-firing bridge
- Existing non-streaming API clients unchanged
- Tests pass without live LLM or Docker when mocked

## Archive Checklist

Move to `prompts-archive/` and update audit + completed README.
