# Agent state orchestration rules

These rules apply whenever Keprix is executing a long, multi-step task using
the `agent_state` tool / `keprix.agent_state` package.

1. **Never execute more than 7 steps in a single chunk/session.** Decompose
   larger work with `action=decompose` (target 5-7 steps per chunk).
2. **Always read state at session start** (`action=read`). Resume from
   `next_step` / `last_completed_step_id`. Do not re-do completed steps.
3. **Always write state after every completed step** (`action=update` with
   `status=completed` and an `output` summary). Record new `decision` and
   `constraint` values as soon as they are discovered.
4. **HALT at every chunk checkpoint.** After finishing a chunk, call
   `pause_for_review`. Do not start the next chunk until a human supplies an
   approval signal (`action=approve` with `human_signal`), then `merge`.
5. **On chunk failure**, call `rollback` (or `reject` which rolls back) and
   wait for human direction. Do not invent a new plan that ignores the
   restored checkpoint.
6. State files are atomic JSON under `~/.keprix/agent-state/` (or
   `KEPRIX_AGENT_STATE_DIR`). Treat them as the source of truth across
   session breaks.
