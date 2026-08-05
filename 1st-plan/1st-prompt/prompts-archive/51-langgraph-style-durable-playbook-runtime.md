# keprix - Prompt 51: LangGraph-Style Durable Playbook Runtime

**Status:** Completed. Implementation in `src/keprix/playbook/runtime/`,
`src/keprix/playbook/run_routes.py`, and `tests/playbook/test_runtime_*.py`.

## Context

Adopt the strongest LangGraph ideas into keprix without making LangGraph a required runtime dependency.

keprix needs long-running, resumable, inspectable workflows for Opportunity Engine, deep research, data analysis, self-coding, browser automation, and security workflows. This prompt builds the durable playbook runtime that all later adoption prompts can use.

Use the product term "playbook". Do not use deprecated recipe terminology in operator-facing text.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/langgraph/README.md
planning/agents-to-adopt/langgraph/libs/checkpoint*
planning/agents-to-adopt/langgraph/examples
```

Adopt concepts:

- State graphs.
- Nodes and edges.
- Conditional branching.
- Subgraphs.
- Durable checkpoints.
- Human interrupts.
- Resumable execution.
- Streaming state updates.

## Files To Create

```text
backend/playbook/runtime/
  __init__.py
  graph.py
  node.py
  edge.py
  state.py
  checkpoint.py
  checkpoint_postgres.py
  checkpoint_sqlite.py
  interrupts.py
  runner.py
  events.py
  errors.py
  serializers.py
tests/playbook/test_runtime_graph.py
tests/playbook/test_runtime_checkpoint.py
tests/playbook/test_runtime_interrupts.py
```

## Required Design

Implement:

```python
class PlaybookGraph:
    add_node(name, handler)
    add_edge(source, target, condition=None)
    add_subgraph(name, graph)
    compile()

class PlaybookRun:
    run_id: str
    graph_id: str
    workspace_id: str
    status: str
    state: dict
```

Execution statuses:

```text
pending
running
interrupted
waiting_for_approval
failed
completed
paused
cancelled
```

## Checkpointing

Support both:

- Postgres checkpoint store.
- SQLite checkpoint store for local installs.

Checkpoint every node transition:

- Input state.
- Output state.
- Node name.
- Timestamp.
- Error, if any.
- Approval request, if any.
- Artifact writes.

## Human Interrupts

Implement interrupt points:

```python
interrupt(reason, state_patch_schema=None, approval_request=None)
resume(run_id, state_patch=None, approved_by=None)
```

Interrupts are required before:

- Spending money.
- Sending messages.
- Publishing.
- Deleting data.
- Modifying CRM records.
- Running high-risk shell or browser actions.

## Streaming Events

Expose run events:

```text
playbook.run.started
playbook.node.started
playbook.node.completed
playbook.node.failed
playbook.interrupted
playbook.approval.requested
playbook.resumed
playbook.completed
```

If the existing observability layer exists, emit events there too.

## API Routes

Add:

```text
GET /api/playbook-runs/{run_id}
GET /api/playbook-runs/{run_id}/events
POST /api/playbook-runs/{run_id}/resume
POST /api/playbook-runs/{run_id}/pause
POST /api/playbook-runs/{run_id}/cancel
```

## Acceptance Criteria

- A graph can run to completion.
- A graph can pause at an interrupt and resume.
- A failed graph can resume from the last checkpoint.
- Postgres and SQLite checkpoint stores share the same interface.
- Events stream in execution order.
- Opportunity Engine phases can be represented as a graph.
- Tests cover branching, subgraphs, checkpoint restore, interrupt resume, and cancelled runs.

