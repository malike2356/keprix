# Keprix - Prompt 294: Deferred tool search hardening

**Pack:** Fable-class product power (292-297)  
**Master reference:** `../prompts-archive/ref-292-fable-class-product-power-master-reference.md`  
**Depends on:** Provider-agnostic tools **291**, existing `tools/tool_search.py`, Hermes progressive disclosure (**280**)

## UI entry point

Primary location: none (runtime)  
Secondary locations: Admin tools / usage metrics for deferred tool loads  
Empty state: n/a  
Discovery trigger: none  
Nav placement: Admin > Tools (metrics only)

## Context

Fable keeps a small always-on tool set and loads the rest via `tool_search`. That is how a product can expose dozens of connectors without destroying the context window.

Keprix already has `tool_search` / `tool_describe` / invoke bridges. This prompt hardens defaults, schema accuracy, and observability so deferred tools are the normal path at scale, not an optional experiment.

## What already exists (do not rebuild)

- `tools/tool_search.py` (core vs deferred, bridge schemas, dispatch)
- Tool registry / `get_tool_schemas()` (**291**)
- MCP tool discovery (`tools/mcp_tool.py`)
- Config shapes under `tools.tool_search`

## What to build

### 1. Default-on policy

When registered tool schemas exceed a token or count threshold:

- Auto-enable deferred mode (`enabled: auto` becomes the default)
- Never defer `_KEPRIX_CORE_TOOLS`
- Never defer the three bridge tools themselves
- Emit a one-line system note: "N tools available via tool_search"

### 2. Schema accuracy contract

After `tool_search` returns a tool:

- Cache exact parameter schema for the session
- Reject guessed parameter names (fail closed with "call tool_search again")
- On empty/unexpected results, require re-search before retry

### 3. Metrics

```python
@dataclass
class DeferredToolStats:
    core_visible: int
    deferred_count: int
    deferred_tokens_saved: int
    searches: int
    invokes: int
    schema_misses: int
```

Expose via `/api/admin/tools/deferred-stats` and Scout signal `tools.deferred_stats`.

### 4. Prompt layer

Update tools layer text:

```text
Deferred tools are not in your active tool list. You MUST call tool_search
before using them. Do not invent parameter names. Use exact names returned
by tool_search / tool_describe.
```

### 5. Tests

- Above threshold: deferred activates
- Core tools remain visible
- Invoke without search fails
- Schema miss increments metric

## Files to create / modify

```
src/keprix/tools/tool_search.py          # defaults + metrics
src/keprix/api/tool_deferred_routes.py   # stats endpoint
src/keprix/agent/layers/tools.py
tests/tools/test_tool_search_hardening.py
docs/features/deferred-tool-search.md
```

## Acceptance criteria

- Large tool catalogs no longer inject full schemas by default.
- Bridge tools are the only way to reach deferred tools.
- Admin can see tokens saved and search/invoke counts.
- Compatible with MCP tools deferred behind the same bridge (**296**).

## Contact

Verlox Ltd: [contact@verlox.uk](mailto:contact@verlox.uk)
