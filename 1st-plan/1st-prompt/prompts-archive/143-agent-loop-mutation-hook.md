# Keprix - Prompt 143: Agent Loop Mutation Hook on Tool Miss

## Context

Read `138-chat-mutation-e2e-wiring-outline.md`.

Complete Prompts **139-142** first.

This is the final prompt in the chat mutation E2E series. It implements Prompt 28's
intended integration: mutation fires when the **tool dispatcher** cannot satisfy
the task, not only when a regex or sidecar bridge guesses a gap.

Output: agent loop / gateway tool routing, `src/keprix/agent/keprix/`,
`tests/mutation/test_agent_loop_mutation.py`, docs update.

## Problem

Prompt 28 specified:

> Called from the main conversation loop BEFORE the tool dispatcher, but only when
> the dispatcher returns "no tool found for task."

That hook was never wired. Prompts 139-142 made `/chat` demoable; this prompt
makes mutation **product-correct** for all channels.

## Step 1: Tool miss signal

In the tool dispatch layer (locate via `grep` for "no tool" / `ToolNotFound` /
dispatcher return codes in `src/keprix/gateway/` and `src/keprix/agent/`):

Define:

```python
class ToolDispatchResult:
    ok: bool
    error_code: Literal["ok", "not_found", "blocked", "failed", ...]
    tool_name: str | None
    message: str
```

When `error_code == "not_found"` or LLM requests unknown tool name:

1. Do not immediately return "I cannot do that"
2. Invoke mutation pipeline with:
   - `task` = original user message (or current turn goal)
   - `available_tools` = `list_runtime_tool_names()`
   - `trigger` = `"tool_miss"`
   - `requested_tool` = tool name LLM asked for (if any)

## Step 2: Mutation pause and resume

After `run_cycle` returns `pending_approval`:

1. Emit `mutation` stream event (same schema as Prompt 139)
2. **Pause** agent loop until approval or rejection (async wait on store record
   status, with timeout configurable via `KEPRIX_MUTATION_APPROVAL_TIMEOUT`)
3. On **approve**: hot-reload registry, resume loop, retry tool call with new name
4. On **reject**: yield assistant text per Prompt 28 rejection copy; end turn

Telegram/Discord inline approve buttons must call the same `ApprovalWorkflow` as
web (already in Prompt 28; verify still wired).

## Step 3: Remove sidecar duplication

When this prompt ships and tests pass:

1. Remove mutation-first call from `_stream_assistant_reply` **or** gate it behind
   `KEPRIX_CHAT_MUTATION_SIDECAR=false` default
2. Single producer for `mutation` events: agent loop only
3. Update `138-chat-mutation-e2e-wiring-outline.md` status section (note sidecar
   retired)

## Step 4: LLM "mutation_requested" signal (optional enhancement)

If the agent loop supports structured assistant tool calls, also trigger mutation when:

- Model outputs `mutation_requested` tool or JSON field
- Confidence from gap detector >= threshold without prior tool miss

Keep behind `KEPRIX_MUTATION_LLM_TRIGGER=true` default off to avoid double triggers
with tool_miss path.

## Step 5: Conversation flow AC (Prompt 28 parity)

Full flow in `/chat`:

```
User: What is the current stock price of Apple?

Agent: (tool miss or gap)
       I don't have a tool that can fetch live stock prices. Let me create one.
       Creating tool: fetch_stock_price...
       Sandbox test: PASSED.
       Awaiting your approval.

       [MutationCard]

User: [Approve]

Agent: Tool approved and installed. Retrying your request now.
       Apple Inc. (AAPL) is currently trading at $213.42...
```

Verify with integration test (mocked LLM + sandbox).

## Step 6: Tests

`tests/mutation/test_agent_loop_mutation.py`:

| Case | Assert |
| --- | --- |
| Dispatcher not_found | `run_cycle` called once |
| Pending approval | loop pauses; no final answer until approve |
| Approve | registry contains new tool; retry succeeds |
| Reject | no install; polite assistant message |
| `KEPRIX_MUTATION_ENABLED=false` | normal "cannot do that" without cycle |
| Recursive guard | generated tool cannot import mutation modules |

Cross-channel smoke: web UI stream (Prompt 142) receives `mutation` from loop, not
bridge.

## Step 7: Documentation

Update `docs/features/agent.md` mutation section:

- Chat integration path (loop hook, not sidecar)
- Env vars table
- Link to `/dashboard/mutations` for owners

## Acceptance Criteria

- Prompt 28 conversation flow AC met through `/chat` without sidecar bridge
- Tool miss in gateway loop triggers mutation (test proves call path)
- Approve/reject/pause/resume works for web stream
- No duplicate mutation cycles per user turn
- `pytest tests/mutation/test_agent_loop_mutation.py` passes
- Marketing hero terminal demo phrase works E2E with Prompt 140 patterns

## Series Completion

When Prompt 143 archives:

1. All five implementation prompts (139-143) in `prompts-archive/`
2. Keep **138** in `pending-prompts/` as permanent reference (or move to
   `planning/prompts/` root as control doc)
3. Update `PROMPT-CROSSREF-GUIDE.md` capability table
4. Optional: add `docs/features/mutation-chat-integration.md` summary pointing to 138

## Archive Checklist

Move to `prompts-archive/` and update audit + completed README.
