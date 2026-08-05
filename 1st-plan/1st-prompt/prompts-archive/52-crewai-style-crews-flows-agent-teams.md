# keprix - Prompt 52: CrewAI-Style Crews, Flows, and Agent Teams

> **Status (2026-07-05):** Returned from `completed/` to `pending-prompts/`. Scaffold lives in `keprix/backend/teams/` only; mount routes on `src/keprix/api/server.py` before re-archiving.

## Context

Adopt CrewAI's strongest ideas into keprix: role-based agent teams, deterministic flows, task objects, lifecycle hooks, and declarative YAML definitions.

keprix should support both autonomy and control:

- Crews: autonomous specialist agents collaborating.
- Flows: deterministic event-driven workflows with explicit control.

These must run on the durable playbook runtime from Prompt 51.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/crewai/README.md
planning/agents-to-adopt/crewai/lib/crewai/crewai/src/crewai
planning/agents-to-adopt/crewai/lib/crewai/crewai/tests
```

Adopt concepts, not code wholesale.

## Files To Create

```text
backend/teams/
  __init__.py
  agent_role.py
  crew.py
  task.py
  flow.py
  yaml_loader.py
  hooks.py
  guardrails.py
  structured_output.py
  registry.py
tests/teams/test_crews.py
tests/teams/test_flows.py
tests/teams/test_yaml_loader.py
```

## Agent Role Model

Each role includes:

- Name.
- Goal.
- Backstory.
- Tools.
- LLM profile.
- Memory scope.
- Guardrails.
- Delegation policy.
- Approval policy.
- Max iterations.
- Structured output schema.

Default roles:

- Researcher.
- Analyst.
- Builder.
- Browser Operator.
- Data Analyst.
- Code Engineer.
- QA Reviewer.
- Compliance Reviewer.
- Launch Operator.

## Task Model

Each task includes:

- Description.
- Expected output.
- Assigned role.
- Dependencies.
- Required artifacts.
- Output schema.
- Human review flag.
- Risk level.
- Timeout.
- Retry policy.

## Flow Model

Flows are deterministic workflows built from events and tasks:

```text
on_start
on_task_completed
on_task_failed
on_approval_received
on_timeout
```

Flows must compile to Prompt 51 playbook graphs.

## YAML Format

Support import/export:

```yaml
name: Opportunity Research Crew
roles:
  researcher:
    goal: Find market demand with citations
tasks:
  demand:
    role: researcher
    output: 01-market-demand.md
flow:
  start: demand
```

## Hooks

Add lifecycle hooks:

- Before task.
- After task.
- On tool call.
- On artifact write.
- On approval request.
- On error.

Hooks should feed Scout bridge events if configured.

## Acceptance Criteria

- Crews can run multiple role-based agents on one objective.
- Flows can run deterministic task graphs.
- YAML definitions can be imported and exported.
- Human review tasks pause the run.
- Structured outputs validate before artifact write.
- Tests cover delegation, dependency ordering, failed task retry, and approval pause.

