# keprix - Prompt 64: Smolagents-Style Code Agent and Hub Tools

## Context

Adopt smolagents' strongest ideas: code-first agents, compact tool abstractions, sandboxed execution providers, modality-agnostic inputs, MCP and external tool collections, and shareable hub agents.

This extends Prompts 05, 07, 15, 36, 44, and 67.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/smolagents/README.md
planning/agents-to-adopt/smolagents/src/smolagents
```

## Files To Create Or Extend

```text
backend/code_agent/
  __init__.py
  code_agent.py
  action_syntax.py
  sandbox_provider.py
  docker_provider.py
  e2b_provider.py
  modal_provider.py
  tool_collection.py
  modality_inputs.py
backend/hub/
  agent_package.py
  tool_package.py
  package_signing.py
tests/code_agent/test_code_agent.py
tests/code_agent/test_sandbox_provider.py
tests/code_agent/test_tool_collection.py
tests/hub/test_agent_package.py
```

## Required Features

### Code Agent Mode

Add an agent mode that plans and acts through generated code snippets, not only natural-language tool calls.

Controls:

- Allowed imports.
- Allowed file paths.
- Network policy.
- Max runtime.
- Memory limit.
- Approval threshold.
- Output schema.

### Sandbox Providers

Support provider interface:

```python
class SandboxProvider:
    def start(self, workspace_id: str) -> SandboxSession: ...
    def run_code(self, session_id: str, code: str) -> SandboxResult: ...
    def stop(self, session_id: str) -> None: ...
```

Implement Docker first. Add optional E2B and Modal adapters only when configured.

### Tool Collections

Load tools from:

- Native keprix tools.
- MCP servers.
- Hub packages.
- Python callable adapters.
- Remote hosted tools.

### Modality Inputs

Normalize text, images, audio transcripts, video summaries, files, and URLs into artifact references before agents use them.

## Acceptance Criteria

- Code agent mode can solve a small data task in Docker.
- Unsafe imports and filesystem access are blocked.
- MCP tools can be mounted as a collection.
- Hub agent packages are signed and verified before install.
- No Hugging Face or smolagents branding appears in keprix UI.

