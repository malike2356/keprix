# Keprix TypeScript SDK

Ergonomic TypeScript client for Keprix agents, playbook workflows, memory, RAG, and evals.
Calls the existing Python backend; it does not embed a second agent runtime.

## Setup

```bash
cd sdk/typescript
npm install
export KEPRIX_API_KEY=kp_...
export KEPRIX_BASE_URL=http://localhost:3333
```

## Examples

```bash
npm run example:agent
npm run example:workflow
npm run example:rag
```

## Modules

| Module | Purpose |
| --- | --- |
| `agent` | Define agents, attach tools/memory, run, stream, trace |
| `workflow` | Step/branch/parallel/retry/approval graphs via playbook runs |
| `memory` | Conversation, observational, retrieval, workspace facts, preferences |
| `rag` | Ingest and search RAG sources; document agent queries |
| `evals` | Define cases, run locally or via API, export reports |
| `tools` | Tool schema helpers for agent definitions |
| `local-dev` | Health checks and manifest fetch for local development |
