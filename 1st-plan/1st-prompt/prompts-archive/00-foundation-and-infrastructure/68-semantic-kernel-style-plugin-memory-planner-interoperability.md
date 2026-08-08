# keprix - Prompt 68: Semantic Kernel-Style Plugin, Memory, Planner, and Interoperability Layer

> **Status (2026-07-05):** Implemented under `src/keprix/kernel/` with plugin contracts, planner, swappable memory backends, MCP/A2A interoperability bridge, `/api/kernel/*` routes, and 6 tests. No third-party branding in UI.

## Context

Adopt Semantic Kernel's durable enterprise ideas: plugin contracts, memory abstractions, planners, multi-provider model support, cross-runtime interoperability, A2A, MCP, and typed function invocation.

This extends Prompts 04, 06, 07, 15, 64, 65, and 98.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/semantic-kernel/README.md
planning/agents-to-adopt/semantic-kernel/python/semantic_kernel
planning/agents-to-adopt/semantic-kernel/dotnet/src/SemanticKernel.Abstractions
```

## Files To Create Or Extend

```text
backend/kernel/
  __init__.py
  plugin_contract.py
  function_contract.py
  planner.py
  memory_provider.py
  model_provider.py
  interoperability.py
  a2a_adapter.py
  mcp_adapter.py
tests/kernel/test_plugin_contract.py
tests/kernel/test_planner.py
tests/kernel/test_memory_provider.py
tests/kernel/test_interoperability.py
```

## Required Features

### Plugin Contract

Define a stable plugin contract:

- Name.
- Version.
- Functions.
- Input schema.
- Output schema.
- Auth requirements.
- Risk level.
- Capability tags.
- Documentation.

### Function Invocation

Support typed function calls across:

- Native Python functions.
- HTTP tools.
- MCP tools.
- Agent tools.
- Playbook nodes.

### Memory Provider Abstraction

Allow memory backends:

- Local SQLite.
- Postgres and pgvector.
- File index.
- External vector database.
- In-memory test provider.

### Planner

Add a planner that can select functions and playbook nodes based on:

- Goal.
- Available plugins.
- Permissions.
- Cost.
- Risk.
- Required output type.

### Interoperability

Expose adapters for:

- MCP.
- A2A.
- OpenAI-compatible API.
- keprix SDK.

## Acceptance Criteria

- A plugin can be loaded, inspected, invoked, and traced.
- Planner refuses tools outside user permissions.
- Memory provider can be swapped in tests.
- MCP and A2A adapters share the same plugin contract.
- No Microsoft or Semantic Kernel branding appears in keprix UI.

