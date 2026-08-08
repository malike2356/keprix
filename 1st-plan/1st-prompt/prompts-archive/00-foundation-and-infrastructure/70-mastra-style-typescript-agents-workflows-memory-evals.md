# keprix - Prompt 70: Mastra-Style TypeScript Agents, Workflows, Memory, and Evals

> **Status (2026-07-05):** Implemented `sdk/typescript/` (agent, workflow, memory, RAG, evals, tools, local-dev), playbook workflow start API, SDK manifest/eval routes, `/developer/sdk` UI, and 7 contract tests.

## Context

Adopt Mastra's useful TypeScript-native app-building patterns: ergonomic agent definitions, graph workflows, conversation history, observational memory, RAG integration, evals, and a developer-friendly local workflow.

This prompt extends the keprix SDK and frontend developer experience. It must not duplicate the Python backend runtime.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/mastra/README.md
planning/agents-to-adopt/mastra/packages
planning/prompts/19-app-foundation-sdk.md
```

## Files To Create Or Extend

```text
sdk/typescript/
  src/agent.ts
  src/workflow.ts
  src/memory.ts
  src/rag.ts
  src/evals.ts
  src/tools.ts
  src/local-dev.ts
  examples/basic-agent.ts
  examples/workflow.ts
  examples/rag-agent.ts
frontend/src/app/developer/sdk/page.tsx
tests/sdk/test_typescript_contracts.py
```

## Required Features

### TypeScript Agent API

Expose a clean TS API:

- Define agent.
- Attach tools.
- Attach memory.
- Run.
- Stream.
- Trace.
- Evaluate.

### Workflow API

Support:

- Step.
- Branch.
- Parallel.
- Retry.
- Human approval.
- Artifact output.

The TypeScript workflow API calls the backend playbook runtime instead of creating a second runtime.

### Memory API

Expose:

- Conversation history.
- Observational memory.
- Retrieval memory.
- Workspace facts.
- User preferences.

### Evals API

Allow developers to:

- Define eval cases.
- Run evals locally.
- Compare outputs.
- Export reports.

## Acceptance Criteria

- TypeScript examples run against a local keprix instance.
- TS workflows map to Prompt 51 playbook runs.
- Memory API respects workspace permissions.
- Evals produce the same trace format as backend evals.
- No Mastra enterprise-only code or copy is imported.

