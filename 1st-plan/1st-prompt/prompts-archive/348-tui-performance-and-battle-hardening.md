# Keprix Prompt 348: TUI Performance and Battle Hardening

## Goal

Make Keprix TUI feel stronger than Hermes under load, failure, and daily use. This prompt turns renderer and runtime improvements into operator-grade hardening: benchmarks, long-session tests, fault injection, terminal matrix checks, memory budgets, and latency budgets.

## Required areas

### Long-session endurance

Test and optimize:

- 10K messages
- 100K transcript lines by virtualized estimate
- 500 tool events in one turn
- 100 subagents in a tree
- 1K queued messages
- 10K input history entries

### Latency budgets

Create explicit budgets:

- Slash picker opens under 50 ms for local commands.
- Slash filtering under 30 ms for 500 commands.
- Transcript append under 16 ms for normal rows.
- 10K message virtual window calculation under 25 ms.
- Interrupt request scheduled under 50 ms.
- Resize refresh under 50 ms for large transcripts.

Use conservative budgets that pass locally, then document them.

### Memory budgets

Track:

- Runtime store memory growth
- Transcript virtualization memory
- Render snapshot memory
- Queue memory
- Search index memory if added

No unbounded growth without caps.

### Fault matrix

Add tests for:

- Backend offline
- Backend restart
- HTTP 400, 401, 403, 404, 408, 429, 500
- Invalid JSON stream line
- Stream stalls
- Tool event missing id
- Subagent event missing id
- Model list unavailable
- Skills/plugins unavailable
- Clipboard unavailable
- Browser opener unavailable
- Editor unavailable
- Terminal too small
- Resize storm
- Ctrl+C spam

### Terminal matrix

Add terminal profile tests for:

- xterm truecolor
- tmux
- screen
- iTerm2
- WezTerm
- Kitty
- Windows Terminal
- VS Code terminal
- Termux
- basic dumb terminal

### Daily-use hardening

Implement:

- Clear error messages
- No tracebacks in normal UI
- Recoverable overlays
- Escape closes overlays
- Help always reachable
- Queue never silently loses user text
- Input focus restored after overlays
- Terminal restored on every exit path

## Tests required

Add:

```text
tests/tui/test_performance_budgets.py
tests/tui/test_long_session_endurance.py
tests/tui/test_fault_matrix.py
tests/tui/test_terminal_matrix.py
tests/tui/test_overlay_recovery.py
tests/tui/test_memory_budgets.py
```

## Acceptance criteria

- Performance budgets pass locally.
- Long-session tests pass without high memory growth.
- Fault matrix tests pass.
- Terminal matrix tests pass.
- No normal-user path emits an unhandled traceback.
- Existing TUI tests pass.
- `bash scripts/check-tui-parity.sh` passes.

## Verification commands

```bash
python -m pytest tests/tui/test_performance_budgets.py -q
python -m pytest tests/tui/test_fault_matrix.py -q
python -m pytest tests/tui/test_terminal_matrix.py -q
python -m pytest tests/tui -q
bash scripts/check-tui-parity.sh
```

