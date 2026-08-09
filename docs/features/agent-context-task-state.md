# Agent context and task state

Keprix keeps a durable JSON project-state file for long multi-step agent work so
context survives session breaks.

## Package

`src/keprix/agent_state/`

| Module | Role |
| --- | --- |
| `context_state.py` | Create / update / read / resume atomic JSON state |
| `task_decomposer.py` | Split plans into 5-7 step chunks (max 5 chunks for a 30-step plan) |
| `checkpoint_validator.py` | Human approval gate between chunks; rollback on failure |
| `AGENTS.md` | Orchestration rules for the agent |

Storage default: `~/.keprix/agent-state/<session_id>/state.json`  
Override: `KEPRIX_AGENT_STATE_DIR`

## Agent tool

Tool name: `agent_state` (toolset `agent_state`)

Typical flow:

1. `create` with `session_id` + task description (optional `steps`)
2. `decompose`
3. `start_chunk` → `update` each step → `pause_for_review`
4. Human `approve` with `human_signal` → `merge`
5. Repeat for the next chunk; on failure `rollback`

At every new session call `read` first. The response includes `next_step`,
`can_proceed`, and an `injection` resume block.

## Rules

See `src/keprix/agent_state/AGENTS.md`. Hard constraints: max 7 steps per chunk,
always read/write state, HALT at checkpoints until a human confirmation signal.
