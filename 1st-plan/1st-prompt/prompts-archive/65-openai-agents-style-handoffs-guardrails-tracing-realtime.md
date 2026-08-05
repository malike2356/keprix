# keprix - Prompt 65: OpenAI Agents-Style Handoffs, Guardrails, Tracing, and Realtime

## Context

Adopt the useful architecture patterns from OpenAI Agents SDK: agents with instructions and tools, handoffs, agents as tools, guardrails, tracing, sandbox agents, and realtime voice agents.

This extends Prompts 65, 70, 71, 83, and 96. Do not make keprix dependent on OpenAI.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/openai-agents-python/README.md
planning/agents-to-adopt/openai-agents-python/src/agents
```

## Files To Create Or Extend

```text
backend/agents_runtime/
  __init__.py
  agent_spec.py
  handoff.py
  guardrail.py
  run_context.py
  realtime.py
  sandbox_agent.py
backend/observability/
  trace_view.py
  trace_export.py
frontend/src/components/traces/AgentTraceViewer.tsx
frontend/src/components/realtime/RealtimeAgentPanel.tsx
tests/agents_runtime/test_handoffs.py
tests/agents_runtime/test_guardrails.py
tests/agents_runtime/test_realtime.py
```

## Required Features

### Agent Spec

Each agent includes:

- Name.
- Instructions.
- Tools.
- Output schema.
- Handoffs.
- Guardrails.
- Model profile.
- Memory scope.
- Approval policy.

### Handoffs

Support controlled delegation:

- Agent A hands to Agent B.
- Human approval handoff.
- Tool handoff.
- Playbook node handoff.

Each handoff must record reason, source, target, context, and accepted state.

### Guardrails

Add input and output guardrails:

- Secret leakage check.
- Financial action check.
- Legal or medical advice check.
- Unsafe browser action check.
- Tool risk check.
- Output schema validation.

### Realtime Agent

Add a realtime voice lane for ECHO-style agents:

- Streaming speech input.
- Streaming speech output.
- Interrupt handling.
- Call transcript.
- Tool approval pause.
- Escalation to text summary.

## Acceptance Criteria

- A support agent can hand off to a billing agent with trace continuity.
- A risky output is blocked by a guardrail and returned for repair.
- Realtime panel streams transcript events.
- Traces show agent, handoff, guardrail, tool, and final output events.
- Provider-specific hosted tools are optional, not required.

