# Keprix - Prompt 139: Chat Mutation Bridge and Runtime Tool Inventory

## Context

Read `138-chat-mutation-e2e-wiring-outline.md` first.

Complete Prompts **28** (mutation engine) and **136** (conversation workspace) first.
Those shipped the engine and UI; this prompt wires them together so `/chat` can
emit real `mutation` stream events instead of only plain LLM text.

Output: `src/keprix/agent/keprix/chat_mutation_bridge.py`,
`src/keprix/agent/keprix/tool_inventory.py`, changes to
`src/keprix/api/conversation_routes.py`, and API tests.

## Problem

Today:

- `POST /api/conversations/{id}/messages` calls `_stream_assistant_reply`
- Non-slash messages go to `stream_chat_completion` only
- `MutationEngine.run_cycle()` is reachable only via
  `POST /api/agent/tools/generated/cycle`
- `conversation_routes.py` already **consumes** `event: "mutation"` but nothing
  **produces** it on the chat path

The `MutationCard` in Prompt 136 is dead UI until this prompt ships.

## Architecture

```
POST /api/conversations/{id}/messages
  event_stream()
    _stream_assistant_reply()
      maybe_run_mutation_for_chat()   <-- NEW (mutation-first)
        list_runtime_tool_names()
        GapDetector.classify()
        MutationEngine.run_cycle()
        yield text_delta + mutation + text_done
      (skip stream_chat_completion when mutation cycle ran)
```

## Step 1: Runtime tool inventory

Create `src/keprix/agent/keprix/tool_inventory.py`:

```python
def list_runtime_tool_names() -> list[str]:
    """Built-in registry names + installed generated tools."""
```

Implementation rules:

1. Import `tools.registry.registry` (same source as slash `/tools`)
2. Merge `registry.get_all_tool_names()` with names from the generated tool store
   for records with `status == "installed"`
3. Deduplicate case-insensitively; return stable sorted list
4. Never raise on missing registry; return `[]` and log once

Add unit tests in `tests/mutation/test_tool_inventory.py`.

## Step 2: Chat mutation bridge

Create `src/keprix/agent/keprix/chat_mutation_bridge.py`:

```python
async def maybe_run_mutation_for_chat(
    *,
    user_text: str,
    user_id: str,
    channel: str = "web_ui",
) -> AsyncIterator[dict[str, Any]]:
```

Behavior:

1. **Gate checks** (return empty iterator if any fail):
   - `get_mutation_config().enabled` is false
   - Governance feature flag blocks `mutation_engine` (use existing governance
     helper if present; otherwise read `feature_flags` store)
   - `agent_stop_requested()` or workspace read-only (caller may already check;
     bridge must not bypass)

2. **Gap detection:**
   - `tools = list_runtime_tool_names()`
   - `gap = get_mutation_engine().detect_gap(user_text, tools)` or equivalent
     `GapDetector.classify` wrapper already on the engine

3. **No gap:** yield nothing (caller continues to LLM path)

4. **Gap found:** emit progressive assistant text, then mutation event:

```
text_delta: "No matching tool for this task. Synthesising one now..."
text_delta: "Running sandbox test..."
```

Then after `run_cycle` completes with `pending_approval` or sandbox-passed pending
record, yield:

```python
{
    "event": "mutation",
    "id": record.id,
    "toolName": record.tool_name,
    "approach": record.gap_description or record.candidate_approach,
    "code": record.tool_code,
    "skillYaml": record.skill_yaml,
    "sandboxResult": (record.sandbox_result or {}).get("stdout", ""),
    "sandboxExitCode": (record.sandbox_result or {}).get("exit_code", 0),
    "sandboxStderr": (record.sandbox_result or {}).get("stderr", ""),
    "status": "pending",
}
```

Finish with:

```
text_delta: "Sandbox passed. Approve the tool card to install and retry."
text_done: ""
```

5. **Failure paths** (must not stub):
   - Sandbox failed after max retries: yield `text_delta` explaining failure; do
     not emit `mutation` with `status: pending`
   - Synthesis blocked by static analyser: yield explicit error text
   - Mutation disabled mid-flight: yield `text_delta` with reason

6. Return a boolean or use a small result object so `_stream_assistant_reply`
   knows whether to skip the LLM fallback.

## Step 3: Wire `_stream_assistant_reply`

File: `src/keprix/api/conversation_routes.py`

In `_stream_assistant_reply`, after slash-command handling and **before**
`stream_chat_completion`:

```python
mutation_ran = False
async for event in maybe_run_mutation_for_chat(
    user_text=user_text,
    user_id=user_id,
    channel="web_ui",
):
    mutation_ran = True
    yield event
if mutation_ran:
    return
```

Preserve existing slash-command and gateway dispatch behavior.

Pass `session_id` into the bridge if the engine needs it for audit records (add
parameter when `MutationEngine.run_cycle` accepts it).

## Step 4: Persist original task for retry

When appending the assistant message in `send_message`, the user message is
already stored. Ensure the mutation `record` in the DB stores:

- `original_task` or equivalent field = user message text
- `session_id` if the schema supports it

If the generated_tools table lacks `session_id`, add a migration in this prompt
or store `session_id` in `record.metadata` JSON. Prompt 141 depends on this.

## Step 5: API tests

Create `tests/api/test_chat_mutation_stream.py`:

1. Mock `ToolSynthesiser` and `SandboxRunner` (same patterns as
   `tests/mutation/test_mutation_engine.py`)
2. POST message with stock-price gap phrase when `fetch_stock_price` not installed
3. Assert NDJSON stream contains `event: mutation` with `toolName`, `code`, `id`
4. Assert assistant message persisted with `type: mutation` block
5. Assert `KEPRIX_MUTATION_ENABLED=false` yields no mutation event (LLM or empty
   fallback only)
6. Assert non-gap message does not call `run_cycle` (mock call count)

Run: `pytest tests/api/test_chat_mutation_stream.py tests/mutation/ -q`

## Configuration

Document in `.env.example` (if not already present from Prompt 28):

```bash
KEPRIX_MUTATION_ENABLED=true
KEPRIX_MUTATION_GAP_CONFIDENCE=0.7
KEPRIX_MUTATION_REQUIRE_APPROVAL=true
```

## Acceptance Criteria

- Sending a gap-triggering message in `/chat` streams a `mutation` NDJSON event
- `MutationCard` renders in the thread without manual API calls
- `list_runtime_tool_names()` includes installed generated tools
- Mutation-first path skips `stream_chat_completion` for that turn
- No `pass`, `TODO`, or "coming soon" in the chat mutation code path
- `pytest tests/api/test_chat_mutation_stream.py` passes
- Grep clean for stub markers in new modules:

```bash
rg -n "TODO|coming soon|NotImplementedError|pass$" \
  src/keprix/agent/keprix/chat_mutation_bridge.py \
  src/keprix/agent/keprix/tool_inventory.py
```

## Archive Checklist

When done:

1. Move this file to `prompts-archive/`
2. Update `pending-prompts/PROMPT-IMPLEMENTATION-AUDIT.md`
3. Update `prompts-archive/README.md` row for Prompt 139
