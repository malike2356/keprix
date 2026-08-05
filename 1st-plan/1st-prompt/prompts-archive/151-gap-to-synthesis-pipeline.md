# Keprix - Prompt 151: Gap-to-Synthesis Pipeline

## Purpose

Wire the full loop from "agent hits a missing tool" to "tool is synthesized,
approved, registered, and available". This prompt connects the already-built
components: `tool_gap_detector.py` fires, `tool_synthesizer.py` (Prompt 150)
generates the tool, `MutationStore` persists it, the operator approval gate
runs (or auto-approves), and `registry.reload_generated_tools()` makes the tool
live. It also exposes REST API endpoints and a CLI command for operators to
manage the synthesized tool queue.

---

## Dependencies

| Prompt | Capability needed |
|---|---|
| 150 | `tool_synthesizer.py`, `tool_sandbox.py`, `MutationStore` with tool methods |
| 143 | `mutation_hook.run_agent_loop_mutation_turn` wired into gateway |
| existing | `improvement/tool_gap_detector.py` produces `ToolGapProposal` |
| existing | `improvement/routes.py` improvement API |

---

## What to Build

### 1. `src/keprix/mutation/hook.py`

The integration point called from the agent loop when a tool call fails with
a "tool not found" error or when `tool_gap_detector` fires after a completed run.

```python
from keprix.improvement.tool_gap_detector import ToolGapProposal, detect_tool_gaps
from keprix.improvement.run_analyzer import RunRecord, ImprovementProposal
from keprix.mutation.tool_synthesizer import synthesize_tool
from keprix.mutation.store import MutationStore

async def on_tool_miss(
    tool_name: str,
    task_context: str,
    run_id: str,
    workspace_id: str,
    store: MutationStore,
) -> str | None:
    """
    Called immediately when the agent loop attempts to invoke a tool that
    does not exist in the registry.

    1. Build a ToolGapProposal from tool_name and task_context.
    2. Call synthesize_tool(proposal, workspace_id).
    3. If synthesis succeeds:
       a. Call store.save_generated_tool() to persist and set status.
       b. If status=="approved", call store.write_tool_to_disk() and
          registry.reload_generated_tools() to hot-load immediately.
       c. Return a message to inject into the agent's context:
          "Tool '{tool_name}' was not found. A replacement was synthesized
          and is now available. Retry the task."
    4. If synthesis fails, return a message explaining the gap to the agent.
    5. Record an LLM usage event (channel="mutation") if usage tracking enabled.

    This function must not raise. Failures are logged and a fallback message returned.
    """

async def on_run_complete(
    record: RunRecord,
    proposals: list[ImprovementProposal],
    workspace_id: str,
    store: MutationStore,
) -> list[str]:
    """
    Called after every agent run completes. Analyzes the run for tool gaps
    that did not surface as immediate tool misses (e.g., the agent worked around
    a missing tool with a suboptimal approach).

    1. Call detect_tool_gaps(record, proposals) to get ToolGapProposal list.
    2. For each gap with confidence >= KEPRIX_MUTATION_SYNTHESIS_MIN_CONFIDENCE
       (default 0.75) and no existing generated or built-in tool with the same name:
         a. synthesize_tool in background (do not block the run completion).
         b. Save and optionally hot-load.
    3. Return list of synthesized tool names (may be empty).

    Background synthesis: use asyncio.create_task or a job queue so run
    completion is not delayed.
    """
```

### 2. Wire `on_tool_miss` into the agent loop

Locate the tool invocation dispatch code. This is likely in
`tools/managed_tool_gateway.py` or `run_agent.py` where tool calls are routed.

Find the error path where an unknown tool name is handled. Currently it returns
an error to the agent. Extend it:

```python
# In the tool dispatch error path:
if tool_not_found and settings.mutation_tool_synthesis:
    synthesis_message = await mutation_hook.on_tool_miss(
        tool_name=requested_tool_name,
        task_context=current_task_context,
        run_id=current_run_id,
        workspace_id=workspace_id,
        store=mutation_store,
    )
    if synthesis_message:
        return tool_result({"synthesis": synthesis_message, "retry": True})
```

### 3. Wire `on_run_complete` into the improvement routes

`src/keprix/improvement/routes.py` already handles run analysis. After proposals
are generated:

```python
# After detect tool gaps and prompt improvements:
if settings.mutation_tool_synthesis:
    asyncio.create_task(
        mutation_hook.on_run_complete(record, proposals, workspace_id, mutation_store)
    )
```

### 4. Operator approval gate

When a tool has `status="staged"` (confidence below auto-approve threshold),
it is saved but NOT written to disk and NOT loaded into the registry. The
operator must approve it via API or UI before it activates.

Add these methods to `MutationStore`:

```python
def approve_mutation(self, mutation_id: str, approved_by: str) -> MutationRecord:
    """
    Set status="approved", approved_by, approved_at.
    For tool mutations: write to disk and call registry.reload_generated_tools().
    Return updated record.
    """

def reject_mutation(self, mutation_id: str, rejected_by: str, reason: str) -> MutationRecord:
    """
    Set status="rejected". Record reason in metadata.
    Return updated record.
    """

def rollback_mutation(self, mutation_id: str, rolled_back_by: str) -> MutationRecord:
    """
    Set status="rolled_back".
    For tool mutations: delete .py file from generated_tools_dir,
    call registry to deregister the tool.
    Create a new mutation_events row with tier matching original, status="rolled_back",
    rollback_of=mutation_id.
    Return the rollback record.
    """
```

Add `deregister_tool(tool_name: str)` to `ToolRegistry` in `tools/registry.py`:

```python
def deregister_tool(self, name: str) -> bool:
    """Remove a tool from the registry. Return True if it existed. Thread-safe."""
```

### 5. REST API - `src/keprix/mutation/routes.py`

All routes require authentication. Staged/rejected mutations visible only to admin
or workspace owner.

```
GET  /api/mutation/tools                     List generated tools (paginated, filterable by status)
GET  /api/mutation/tools/{id}                Get single generated tool record
POST /api/mutation/tools/{id}/approve        Approve a staged tool
POST /api/mutation/tools/{id}/reject         Reject a staged tool
POST /api/mutation/tools/{id}/rollback       Roll back an approved tool
GET  /api/mutation/tools/{id}/source         Return raw Python source of generated tool
POST /api/mutation/synthesize                Manually trigger synthesis for a named tool gap
GET  /api/mutation/queue                     Staged mutations awaiting approval (admin)
GET  /api/mutation/stats                     Counts by tier and status
```

Request body for `POST /api/mutation/synthesize`:
```json
{
  "tool_name": "string",
  "description": "string",
  "example_task": "string (optional)"
}
```

Response for list endpoints:
```json
{
  "items": [ MutationRecord ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

### 6. CLI command

Add `keprix mutation` command group to `cli.py` or a new `mutation_cli.py`:

```
keprix mutation list [--status staged|approved|rejected] [--tier tool|prompt|code]
keprix mutation approve <id>
keprix mutation reject <id> --reason "..."
keprix mutation rollback <id>
keprix mutation synthesize --name <tool_name> --description "..."
keprix mutation stats
```

### 7. Add mutation synthesis minimum confidence config

```bash
KEPRIX_MUTATION_SYNTHESIS_MIN_CONFIDENCE=0.75
```

Below this confidence, `on_run_complete` does not trigger background synthesis.
`on_tool_miss` always attempts synthesis (any confidence, because the tool was
explicitly requested and failed).

---

## Acceptance Criteria

1. When the agent calls a tool named `"send_sms"` that does not exist,
   `on_tool_miss` synthesizes a `send_sms` tool (mock LLM), saves it, hot-loads
   it, and returns a retry message. Calling `registry.get_tool("send_sms")` after
   the call returns a registered entry.

2. A synthesized tool with confidence 0.70 (below threshold 0.85) is saved with
   `status="staged"`. It is NOT written to disk. It is NOT in the registry.
   `POST /api/mutation/tools/{id}/approve` writes it to disk, loads it, and
   `registry.get_tool(name)` returns it.

3. `POST /api/mutation/tools/{id}/rollback` removes the `.py` file, deregisters
   the tool, and `registry.get_tool(name)` returns None afterward.

4. `POST /api/mutation/synthesize` with a valid name and description triggers
   synthesis and returns 202 Accepted with the mutation record id.

5. `GET /api/mutation/stats` returns a JSON object with counts grouped by tier
   and status.

6. `keprix mutation list --status staged` prints a table of pending approvals.

7. `on_run_complete` with a run record that has a tool gap and confidence 0.90
   creates a background synthesis task. The task completes and the tool is
   available within 30 seconds (in tests: await the task directly).

8. Two simultaneous `on_tool_miss` calls for the same tool name result in only
   one synthesis (deduplication: check for existing staged or approved mutation
   with the same name before synthesizing).

---

## Tests

### `tests/mutation/test_hook.py`

```python
def test_on_tool_miss_synthesizes_and_hot_loads(mock_synthesizer, mock_registry)
def test_on_tool_miss_deduplicates(mock_synthesizer, mock_registry)
def test_on_tool_miss_returns_fallback_on_failure(mock_synthesizer_fail)
def test_on_run_complete_triggers_background_synthesis(mock_synthesizer)
def test_on_run_complete_skips_below_confidence_threshold()
def test_on_run_complete_skips_existing_tool()
```

### `tests/mutation/test_mutation_routes.py`

```python
def test_list_generated_tools_returns_paginated()
def test_approve_staged_tool_writes_to_disk_and_loads()
def test_reject_staged_tool_stays_staged()
def test_rollback_approved_tool_deregisters()
def test_synthesize_endpoint_returns_202()
def test_stats_endpoint_returns_counts()
def test_unauthorized_cannot_access_mutation_api()
```

### `tests/integration/test_mutation_e2e.py`

```python
def test_full_loop_tool_miss_to_registered(mock_llm, tmp_generated_dir)
    # 1. Start with empty registry (no "fetch_weather" tool)
    # 2. Call on_tool_miss("fetch_weather", ...)
    # 3. Assert tool is in registry
    # 4. Assert .py file exists on disk
    # 5. Assert mutation_events row with status="approved"
    # 6. Call rollback. Assert tool removed from registry and disk.
```

---

## What This Prompt Does NOT Do

- Prompt/persona mutation (Prompt 152).
- Self-coding mutation (Prompt 153).
- Quality scoring (Prompt 154).
- Operator governance UI (Prompt 155).
- The `POST /api/mutation/synthesize` endpoint is the only manual trigger;
  automated triggers from playbook failures are added in Prompt 154.
