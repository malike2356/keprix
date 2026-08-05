# Keprix - Prompt 193: Mutation Web Chat Wiring Gaps (Prompt 28 E2E)

**Status:** Completed 2026-07-06. Tests: `test_web_chat_stock_price_e2e`, `test_agent_loop_mutation`.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Mutation engine core | `src/keprix/agent/keprix/mutation.py`, `gap_detector.py`, `synthesiser.py`, `sandbox.py` |
| Web stream mutation turn | `src/keprix/interfaces/web_ui_stream.py` -> `run_agent_loop_mutation_turn` |
| Chat mutation events + approve/reject | `src/keprix/api/conversation_routes.py` |
| In-chat mutation UI | `frontend/src/components/workspace/blocks/MutationCard.tsx`, `MutationApprovalPanel.tsx` |
| Stock price gap + loop tests | `tests/mutation/test_gap_detector.py`, `test_agent_loop_mutation.py` |

## Gaps this prompt closes

1. **Dual synthesis paths** - `src/keprix/mutation/hook.py` (`on_tool_miss`) and `src/keprix/agent/keprix/mutation_hook.py` (`run_cycle`) still diverge
2. **Agent loop off by default** - `KEPRIX_WEB_UI_AGENT_LOOP=false` in `.env.example`; owners get LLM-only chat after gap check passes
3. **No owner auto-enable** - `web_ui_stream.py` does not call `effective_access_level()` to default the loop on for developers/admins

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Step 1: Unify tool-miss dispatch

Create `src/keprix/agent/keprix/mutation_dispatch.py` with one entry into `MutationEngine.run_cycle()`.

Wire:

- `mutation/hook.py` `on_tool_miss` -> delegate (sync message mode)
- `mutation_hook.py` `handle_tool_miss_stream` -> same core (stream mode)

Remove duplicate synthesis in `mutation/hook.py` after delegation.

## Step 2: Owner-default agent loop

In `web_ui_stream.py`:

```python
def web_ui_agent_loop_enabled() -> bool:
    raw = os.environ.get("KEPRIX_WEB_UI_AGENT_LOOP")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    from keprix.keys.local_access import effective_access_level
    return effective_access_level() in {"developer", "admin", "owner"}
```

Update `.env.example` comment (keep explicit `false` override documented).

## Step 3: Web stock price E2E test (thin)

Add `tests/mutation/test_web_chat_stock_price_e2e.py` that exercises NDJSON stream from `iter_web_ui_gateway_stream` with mocked LLM/sandbox (extend patterns from `test_agent_loop_mutation.py`, do not duplicate unit tests).

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | `on_tool_miss` and stream path share one `run_cycle` call site |
| 2 | Owner session: agent loop runs without setting `KEPRIX_WEB_UI_AGENT_LOOP` |
| 3 | `pytest tests/mutation/test_web_chat_stock_price_e2e.py` passes |
| 4 | Existing `tests/mutation/test_agent_loop_mutation.py` still passes |

## Archive

When AC pass.
