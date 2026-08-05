# Keprix Prompt 330: Sessions Memory and Checkpoints Parity

## Purpose

Match Hermes behavior for sessions, memory, checkpoints, resume, and compression while preserving Keprix brain graph, Agent OS run ledger, structured workspace memory, and audit features.

## Preconditions

Complete Prompt 327 inventory first.

## Tasks

1. Compare Hermes and Keprix:
   - session creation
   - session IDs
   - resume behavior
   - branch or fork behavior
   - checkpoints
   - rollback
   - transcript persistence
   - memory search and insertion
   - compression
   - file-backed state
2. Identify differences that are bugs versus Keprix product extensions.
3. Port missing Hermes stability behavior into core session code.
4. Keep Keprix additions through observers or secondary stores:
   - brain graph nodes and edges
   - Agent OS run ledger
   - Scout evidence events
   - structured memory
5. Add migration tests for old and new state names if the rename prompts have run.

## Acceptance criteria

- Resume works after normal exit.
- Resume works after interrupted turn where supported.
- Checkpoint create/list/rollback behavior is tested.
- Keprix brain and Agent OS side effects remain intact.
- Core session code does not import product modules directly.

## Verification

```bash
python -m pytest tests/memory tests/brain tests/agent tests/upgrade -q
python -m pytest tests/agent_os tests/architecture -q
```
