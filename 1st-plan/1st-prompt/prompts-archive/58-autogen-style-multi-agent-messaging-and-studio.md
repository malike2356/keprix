# keprix - Prompt 58: AutoGen-Style Multi-Agent Messaging and Studio

## Context

Adopt the useful AutoGen ideas into keprix: multi-agent message passing, agent-as-tool composition, MCP workbench patterns, streaming console output, and a visual builder for agent teams.

AutoGen itself is in maintenance mode, so do not make it a hard dependency. Copy concepts, not runtime lock-in.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/autogen/README.md
```

## Files To Create

```text
backend/multiagent/
  __init__.py
  message.py
  runtime.py
  agent_tool.py
  group_chat.py
  workbench.py
  stream.py
  registry.py
frontend/src/app/agent-studio/page.tsx
frontend/src/components/agent-studio/AgentCanvas.tsx
frontend/src/components/agent-studio/AgentRolePanel.tsx
frontend/src/components/agent-studio/ToolWorkbenchPanel.tsx
frontend/src/components/agent-studio/RunStreamPanel.tsx
tests/multiagent/test_message_runtime.py
tests/multiagent/test_agent_tool.py
tests/multiagent/test_group_chat.py
```

## Message Runtime

Implement:

- Agent messages.
- Tool messages.
- Approval messages.
- System messages.
- Artifact references.
- Run events.

Messages must include:

- Sender.
- Recipient.
- Workspace ID.
- Run ID.
- Content.
- Metadata.
- Timestamp.
- Trace ID.

## Agent As Tool

Expose specialist agents as callable tools:

```python
AgentTool(agent_id="math_expert")
AgentTool(agent_id="researcher")
AgentTool(agent_id="browser_operator")
```

Use cases:

- General assistant can call a specialist.
- Opportunity Engine can call Researcher, Analyst, Asset Builder, Compliance Reviewer.
- Coding agent can call QA Reviewer.

## Group Chat

Implement governed group chats:

- Round robin.
- Supervisor moderated.
- Vote and decide.
- Debate then summarize.
- Human review before final action.

## MCP Workbench

Build a workbench abstraction for one or more MCP servers:

- List tools.
- Validate trusted server.
- Bind tools to agent.
- Log all tool calls.
- Require approval for dangerous tools.

## Agent Studio

Build a compact visual builder:

- Create agent roles.
- Assign tools.
- Connect agents.
- Define group chat policy.
- Save as playbook YAML.
- Run in dry-run mode.

Do not make this a marketing page. It is an operator tool.

## Acceptance Criteria

- Agents can send structured messages to each other.
- One agent can call another as a tool.
- Group chat supports at least two policies.
- MCP workbench lists and binds tools with risk labels.
- Agent Studio can save a basic multi-agent playbook.
- Tests cover message routing, agent tool calls, group chat policy, and MCP risk gating.

