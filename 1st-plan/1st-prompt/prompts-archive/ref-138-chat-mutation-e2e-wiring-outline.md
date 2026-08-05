# Keprix - Prompt 138: Chat Mutation End-to-End Wiring Outline (Reference)

## Purpose

This document preserves the architecture and wiring plan for making the marketing
terminal demo **true end-to-end in `/chat`**. It is a **reference and dependency
map**, not an implementation prompt by itself.

Build the behavior through Prompts **139-143** in numeric order. Do not archive
this file; keep it as the source of truth for cross-prompt acceptance criteria.

## Implementation status (2026-07-06)

| Prompt | Status |
| --- | --- |
| 139 | Archived: chat mutation bridge + tool inventory |
| 140 | Archived: gap detector LLM classifier |
| 141 | Archived: approve retry + chat follow-up |
| 142 | Archived: WEB_UI gateway NDJSON stream |
| 143 | Archived: agent loop tool-miss hook |

The Prompt 139 sidecar bridge is retired by default (`KEPRIX_CHAT_MUTATION_SIDECAR=false`).
Mutation NDJSON events now originate from `mutation_hook.run_agent_loop_mutation_turn`
inside the gateway stream path.

## Dependencies

Complete these prompts first (already archived):

| Prompt | Capability |
| --- | --- |
| 28 | Mutation engine (gap detect, synthesise, sandbox, approval, install) |
| 136 | Agent conversation workspace (`MutationCard`, NDJSON stream consumer) |
| 137 | Admin mutation queue (`/dashboard/mutations`) |
| 71 | Interface registry and gateway dispatch |

## Current State (Post 139-143)

```
User message in /chat
  -> POST /api/conversations/{id}/messages
  -> _stream_assistant_reply
       -> KEPRIX_CHAT_GATEWAY_STREAM=true (default)
            -> registry.dispatch_stream(WEB_UI, stream=True)
            -> iter_web_ui_gateway_stream
                 -> slash? -> slash handler (word-streamed)
                 -> evaluate_turn_tool_miss (mutation_hook)
                 -> run_cycle on gap / tool_miss -> event: mutation
                 -> optional KEPRIX_WEB_UI_AGENT_LOOP -> full agent loop
                 -> else stream_chat_completion (LLM fallback)
       -> KEPRIX_CHAT_GATEWAY_STREAM=false (legacy)
            -> optional KEPRIX_CHAT_MUTATION_SIDECAR=true -> chat_mutation_bridge
            -> else stream_chat_completion only
User: Approve on MutationCard
  -> POST /api/mutations/{id}/approve?session_id=...
  -> LiveInstaller + KeprixRetry.retry_message persisted to session
```

**Shipped (139-143):**

- `chat_mutation_bridge.py` + `tool_inventory.py` (sidecar; off by default)
- `mutation_hook.py` + `tool_dispatch.py` (primary path via gateway stream)
- `gap_detector.py` LLM classifier + `track_time` demo pattern
- Generic `KeprixRetry`, approve API `retry_message`, `MutationCard` / `useChat`
- `web_ui_stream.py`, `dispatch_stream`, `KEPRIX_CHAT_GATEWAY_STREAM`
- NDJSON consumer for `event: "mutation"` in `conversation_routes.py`
- `MutationCard` with Approve/Reject calling `/api/mutations/{id}/approve`
- Admin mutation queue at `/dashboard/mutations`
- Tests: `test_chat_mutation_stream.py`, `test_mutation_approve_retry.py`,
  `test_web_ui_stream.py`, `test_agent_loop_mutation.py`

**Optional / not default:**

- `KEPRIX_WEB_UI_AGENT_LOOP=true` for full tool-calling agent in web chat (needs configured provider)
- `KEPRIX_CHAT_MUTATION_SIDECAR=true` to restore Prompt 139 sidecar before agent loop hook

**Remaining product gaps (outside this series):**

- Pause-until-approve inside the Hermes `conversation_loop` sync path (web stream uses
  `wait_for_approval=false` by default; user approves via MutationCard after stream ends)
- Every arbitrary chat message auto-mutating without a detectable gap or tool miss

## Target Flow (What "True" Looks Like)

```
User: Track my time on this project
  -> GapDetector.classify(task, available_tools) -> has_gap=true
  -> MutationEngine.run_cycle(task, tools)
  -> stream event: mutation (code, sandbox, id, status=pending)
  -> MutationCard in chat thread
User: Approve
  -> POST /api/mutations/{id}/approve
  -> LiveInstaller registers tool
  -> retry original task with new tool
  -> assistant message with real result
```

## Phase Map (Implementation Prompts)

| Phase | Prompt | Outcome |
| --- | --- | --- |
| 1 | 139 | Chat mutation bridge, runtime tool inventory, NDJSON emission |
| 2 | 140 | Gap detector LLM classifier + demo patterns (time tracking) |
| 3 | 141 | Generic `KeprixRetry`, approve API retry payload, chat follow-up |
| 4 | 142 | Gateway `WEB_UI` NDJSON stream bridge |
| 5 | 143 | Agent loop hook on missing tool / tool failure |

## Phase 1 Detail: Minimal Bridge in Conversation API

### New module

`src/keprix/agent/keprix/chat_mutation_bridge.py`

```python
async def maybe_run_mutation_for_chat(
    *,
    user_text: str,
    user_id: str,
    channel: str = "web_ui",
) -> AsyncIterator[dict[str, Any]]:
    # yield text_delta / mutation / text_done events
```

Responsibilities:

1. Check `KEPRIX_MUTATION_ENABLED` and governance `mutation_engine` feature flag
2. Load real `available_tools` from tool registry (built-in + MCP + installed mutations)
3. Call `get_mutation_engine().detect_gap(user_text, available_tools)`
4. If `has_gap`, call `await run_cycle(...)`
5. Map `record` to stream shape:

```json
{
  "event": "mutation",
  "id": "<record.id>",
  "toolName": "<record.tool_name>",
  "approach": "<record.gap_description>",
  "code": "<record.tool_code>",
  "skillYaml": "<record.skill_yaml>",
  "sandboxResult": "<stdout>",
  "sandboxExitCode": 0,
  "sandboxStderr": "",
  "status": "pending"
}
```

6. Emit short assistant `text_delta` lines matching the terminal demo script

### Wire into `_stream_assistant_reply`

In `src/keprix/api/conversation_routes.py`, before `stream_chat_completion`:

- Iterate `maybe_run_mutation_for_chat(...)` and yield events
- **Mutation-first policy** for Prompt 139: if gap detected and cycle started, skip generic LLM reply

### Tool inventory helper

`list_runtime_tool_names()`:

- Source: `tools.registry.registry.get_all_tool_names()`
- Include installed mutation tools from generated tool store
- Pass into `run_cycle(task, available_tools)`

## Phase 2 Detail: Gap Detection for Real User Tasks

`GapDetector` today is mostly regex (stock, email, calendar, SQL). "Track my time"
will not trigger mutation without changes.

Options (build in Prompt 140):

1. **Demo patterns:** `time track`, `timer`, `timesheet` -> `track_time` candidate
2. **LLM gap classifier:** replace `_llm_classify` regex stub with real `async_call_llm` JSON output
3. **Tool-loop signal (Prompt 143):** agent emits missing-tool signal from dispatcher

For marketing parity, combine (1) for the demo phrase and (3) for production.

## Phase 3 Detail: Post-Approval Retry in Chat

Today `ApprovalWorkflow.approve()` calls `KeprixRetry.retry()`, which only handles
stock tickers.

Needed:

- `KeprixRetry.retry(task, tool_name, session_id)` generic handler lookup
- Extend `POST /api/mutations/{id}/approve` to return `{ record, retry_message }`
- `MutationCard` / `useChat` append retry assistant text on approve

## Phase 4 Detail: Gateway Stream Bridge

Replace or augment `stream_chat_completion` with:

```python
await registry.dispatch(
    "default",
    InterfaceKind.WEB_UI,
    message=user_text,
    user_id=user_id,
    session_id=session_id,
    stream=True,
)
```

Work:

- Extend `_web_ui_handler` / gateway runner to emit NDJSON (`tool_call`, `mutation`, `text_delta`)
- Map gateway events to `conversation_routes` block types

## Phase 5 Detail: Agent Loop Hook

In agent loop / gateway tool router:

```
LLM selects tool -> not found / tool error
  -> MutationEngine.run_cycle(task, available_tools)
  -> pause for approval
  -> on approve, re-enter loop with new tool registered
```

## Infrastructure and Policy Gates

| Requirement | Why |
| --- | --- |
| `KEPRIX_MUTATION_ENABLED=true` | Master switch |
| Docker or sandbox backend | `SandboxRunner` needs isolated exec |
| LLM provider configured | `ToolSynthesiser` calls LLM |
| `KEPRIX_MUTATION_REQUIRE_APPROVAL=true` | Matches "Approve? [Y/n]" |
| Governance `mutation_engine` flag | Scout can block |
| Generated tools dir writable | `LiveInstaller` install path |

Emit explicit chat error events when mutation is disabled or sandbox fails; do not
silently fall back to generic LLM text.

## Files Checklist

**Backend**

- `src/keprix/api/conversation_routes.py`
- `src/keprix/agent/keprix/chat_mutation_bridge.py` (new, Prompt 139)
- `src/keprix/agent/keprix/gap_detector.py` (Prompt 140)
- `src/keprix/agent/keprix/retry.py` (Prompt 141)
- `src/keprix/agent/keprix/approval.py` (Prompt 141)
- `src/keprix/agent/keprix/mutation_hook.py` (Prompt 143)
- `src/keprix/agent/keprix/tool_dispatch.py` (Prompt 143)
- `src/keprix/interfaces/web_ui_stream.py` (Prompt 142)

**Frontend** (mostly done in Prompt 136)

- `frontend/src/hooks/useChat.ts`
- `frontend/src/components/workspace/blocks/MutationCard.tsx`
- `frontend/src/lib/workspace-api.ts`
- `frontend/src/components/chat/ChatEmptyState.tsx` (optional demo starter)

**Tests**

- `tests/api/test_chat_mutation_stream.py` (Prompt 139)
- Extend `tests/mutation/test_mutation_engine.py`
- `tests/api/test_mutation_approve_retry.py` (Prompt 141)
- Gateway stream tests (Prompt 142)
- Agent loop mutation tests (Prompt 143)

## Suggested Build Order

| Step | Prompt | Effort | Outcome |
| --- | --- | --- | --- |
| 1 | 139 | 1-2 days | Demo works in `/chat` for crafted prompts |
| 2 | 140 | 1-2 days | Demo phrase ("track my time") works reliably |
| 3 | 141 | 1 day | "Installed. Retrying..." is a real tool result |
| 4 | 142 | 3-5 days | All channels share one mutation stream path |
| 5 | 143 | 2-3 days | Matches Prompt 28 conversation flow fully |

## Honest Scope Note

Prompts 139-143 are complete. The marketing terminal demo works in `/chat` for
supported gap phrases (e.g. stock price, time tracking) with real synthesis,
sandbox, approval, and install. Mutation events originate from the agent loop
tool-miss hook by default (`KEPRIX_CHAT_MUTATION_SIDECAR=false`).

Not every chat message auto-mutates; only messages where gap detection or tool
miss identifies a missing capability. Enable `KEPRIX_WEB_UI_AGENT_LOOP=true` for
full tool-loop behavior when a provider is configured.

## Cross-References

- Prompt 28: mutation engine modules and acceptance criteria
- Prompt 136: `MutationCard`, stream block types, approve endpoints
- Marketing hero terminal copy: `frontend/src/components/marketing/Hero.tsx`
