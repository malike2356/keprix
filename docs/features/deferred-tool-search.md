# Deferred tool search hardening

When the registered tool catalog is large, Keprix keeps a small always-on core tool set and loads the rest through bridge tools: `tool_search`, `tool_describe`, and `tool_call` (Prompt 294).

## Defaults

`tools.tool_search.enabled` defaults to `auto`. Deferred mode activates when either:

- deferrable schema tokens exceed `threshold_pct` of the model context window (default 10%), or
- deferrable tool count reaches `count_threshold` (default 40)

Core tools (`_KEPRIX_CORE_TOOLS`) and the three bridge tools are never deferred.

When active, the tools layer includes:

```text
N tools available via tool_search
```

plus a hard rule: call `tool_search` before using deferred tools; never invent parameter names.

## Schema accuracy

After `tool_search` / `tool_describe`, exact parameter schemas are cached for the session. `tool_call` fails closed if:

- the tool was never searched/described this session, or
- argument keys are not in the cached schema

Empty or unexpected describe/search results require a re-search before retry.

## Metrics

`DeferredToolStats` tracks:

- `core_visible`, `deferred_count`, `deferred_tokens_saved`
- `searches`, `describes`, `invokes`, `schema_misses`

Admin: `GET /api/admin/tools/deferred-stats`  
Scout: `tools.deferred_stats`

## Implementation

- `src/keprix/tools/tool_search.py`
- `src/keprix/api/tool_deferred_routes.py`
- `src/keprix/agent/layers/tools.py`
- Executor / `model_tools` bridge unwrap enforces the schema cache
